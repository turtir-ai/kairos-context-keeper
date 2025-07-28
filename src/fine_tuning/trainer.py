import os
import json
import logging
import asyncio
import asyncpg
import torch
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import uuid

try:
    from transformers import (
        AutoTokenizer, 
        AutoModelForCausalLM,
        BitsAndBytesConfig,
        TrainingArguments,
        Trainer as HFTrainer,
        DataCollatorForLanguageModeling
    )
    from peft import (
        LoraConfig, 
        TaskType,
        get_peft_model,
        prepare_model_for_kbit_training
    )
    from datasets import Dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    logging.warning("Hugging Face libraries not available. Fine-tuning disabled.")

# Logger
logger = logging.getLogger(__name__)

class FineTuningTrainer:
    """Advanced trainer for fine-tuning models using failed task data with QLoRA"""

    def __init__(self, db_config: Dict[str, str], model_name: str = "mistralai/Mistral-7B-v0.1"):
        self.db_config = db_config
        self.db_pool = None
        self.model_name = model_name
        self.adapter_base_path = Path("models/lora_adapters")
        self.adapter_base_path.mkdir(parents=True, exist_ok=True)
        
        # QLoRA configuration
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        ) if HF_AVAILABLE else None
        
        self.lora_config = LoraConfig(
            r=16,  # Rank
            lora_alpha=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.1,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        ) if HF_AVAILABLE else None

    async def initialize(self):
        """Initialize database connection pool"""
        self.db_pool = await asyncpg.create_pool(**self.db_config)
        logger.info("✅ Database connection pool initialized for fine-tuning")

    async def close(self):
        """Close database connection pool"""
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database connection pool closed")

    async def fetch_training_data(self, limit: int = None) -> List[Dict[str, str]]:
        """Fetch labeled fine-tuning data from database"""
        if not self.db_pool:
            raise Exception("Database not initialized")

        query = """
            SELECT 
                id, task_id, prompt, correct_output, 
                model_key, task_type, failure_reason,
                guardian_feedback
            FROM fine_tuning_ready
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query)
            return [
                {
                    "id": row['id'],
                    "task_id": row['task_id'],
                    "prompt": row['prompt'],
                    "completion": row['correct_output'],
                    "model_key": row['model_key'],
                    "task_type": row['task_type'],
                    "failure_reason": row['failure_reason'],
                    "guardian_feedback": row['guardian_feedback']
                } 
                for row in rows
            ]

    def prepare_dataset(self, training_data: List[Dict[str, str]]):
        """Prepare dataset in the format required for fine-tuning"""
        if not HF_AVAILABLE:
            raise ImportError("Hugging Face libraries required for dataset preparation")
            
        # Format data for instruction fine-tuning
        formatted_data = []
        for item in training_data:
            # Create instruction-following format
            text = f"""### Instruction:
{item['prompt']}

### Response:
{item['completion']}
"""
            formatted_data.append({"text": text, "id": item['id']})
        
        return Dataset.from_list(formatted_data)

    async def fine_tune_model(
        self, 
        training_data: List[Dict[str, str]], 
        output_dir: Optional[str] = None,
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-4
    ) -> str:
        """Fine-tune the model using QLoRA"""
        if not HF_AVAILABLE:
            logger.error("Hugging Face libraries not available for fine-tuning")
            return None
            
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"🔧 Starting fine-tuning on {device}")

        # Generate unique adapter name
        adapter_name = f"adapter_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        if not output_dir:
            output_dir = self.adapter_base_path / adapter_name
            
        # Load model with 4-bit quantization
        logger.info(f"Loading model: {self.model_name}")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=self.bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"
        
        # Prepare model for k-bit training
        model = prepare_model_for_kbit_training(model)
        
        # Get LoRA model
        model = get_peft_model(model, self.lora_config)
        model.print_trainable_parameters()
        
        # Prepare dataset
        dataset = self.prepare_dataset(training_data)
        
        # Tokenize dataset
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                truncation=True,
                padding="max_length",
                max_length=512
            )
        
        tokenized_dataset = dataset.map(tokenize_function, batched=True)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            warmup_steps=100,
            logging_steps=10,
            save_steps=100,
            learning_rate=learning_rate,
            fp16=True,
            logging_dir=str(output_dir / "logs"),
            save_total_limit=3,
            load_best_model_at_end=True,
            report_to=["tensorboard"],
            remove_unused_columns=False,
        )
        
        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False,
        )
        
        # Initialize trainer
        trainer = HFTrainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=data_collator,
        )
        
        # Train
        logger.info(f"🚀 Starting training with {len(training_data)} samples")
        trainer.train()
        
        # Save adapter
        model.save_pretrained(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))
        
        # Save metadata
        metadata = {
            "adapter_name": adapter_name,
            "base_model": self.model_name,
            "training_samples": len(training_data),
            "training_completed": datetime.now().isoformat(),
            "hyperparameters": {
                "num_epochs": num_epochs,
                "batch_size": batch_size,
                "learning_rate": learning_rate,
                "lora_r": self.lora_config.r,
                "lora_alpha": self.lora_config.lora_alpha
            }
        }
        
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
        # Mark samples as trained in database
        await self._mark_samples_trained([item["id"] for item in training_data], adapter_name)
        
        logger.info(f"✅ LoRA adapter saved to {output_dir}")
        return adapter_name

    async def _mark_samples_trained(self, sample_ids: List[int], batch_id: str):
        """Mark samples as used in training"""
        if not self.db_pool:
            return
            
        async with self.db_pool.acquire() as conn:
            # Convert Python list to PostgreSQL array
            await conn.execute(
                "SELECT mark_samples_trained($1, $2::INTEGER[])",
                batch_id, sample_ids
            )
            logger.info(f"Marked {len(sample_ids)} samples as trained")

    async def get_training_stats(self) -> Dict[str, any]:
        """Get statistics about fine-tuning dataset"""
        if not self.db_pool:
            raise Exception("Database not initialized")
            
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT 
                    COUNT(*) as total_samples,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'labeled' THEN 1 ELSE 0 END) as labeled,
                    SUM(CASE WHEN status = 'trained' THEN 1 ELSE 0 END) as trained
                FROM fine_tuning_dataset
                """
            )
            
            model_stats = await conn.fetch(
                "SELECT * FROM fine_tuning_stats"
            )
            
            return {
                "summary": dict(stats),
                "by_model": [dict(row) for row in model_stats]
            }

    def list_adapters(self) -> List[Dict[str, any]]:
        """List all available LoRA adapters"""
        adapters = []
        
        for adapter_dir in self.adapter_base_path.iterdir():
            if adapter_dir.is_dir():
                metadata_path = adapter_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        metadata["path"] = str(adapter_dir)
                        adapters.append(metadata)
                        
        return sorted(adapters, key=lambda x: x.get("training_completed", ""), reverse=True)


async def main():
    """Example usage"""
    trainer = FineTuningTrainer(
        db_config={
            'host': 'localhost',
            'port': 5432,
            'database': 'kairos_db',
            'user': 'kairos_user',
            'password': 'secure_password'
        }
    )
    
    try:
        await trainer.initialize()
        
        # Get training stats
        stats = await trainer.get_training_stats()
        logger.info(f"Training stats: {stats}")
        
        # Fetch training data
        training_data = await trainer.fetch_training_data(limit=100)
        
        if training_data:
            logger.info(f"Found {len(training_data)} samples for training")
            
            # Fine-tune model
            adapter_name = await trainer.fine_tune_model(
                training_data,
                num_epochs=3,
                batch_size=4
            )
            
            logger.info(f"Training completed. Adapter: {adapter_name}")
        else:
            logger.info("No training data available")
            
    finally:
        await trainer.close()


if __name__ == "__main__":
    asyncio.run(main())
