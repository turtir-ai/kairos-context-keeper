#!/usr/bin/env python3
"""
Kairos Fine-Tuning CLI Command
Usage: python -m src.cli.fine_tune [options]
"""

import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.fine_tuning.trainer import FineTuningTrainer

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('fine_tuning.log')
        ]
    )

async def main():
    """Main fine-tuning CLI function"""
    parser = argparse.ArgumentParser(description='Kairos Model Fine-Tuning')
    parser.add_argument(
        '--model', 
        type=str, 
        default='mistralai/Mistral-7B-v0.1',
        help='Base model to fine-tune'
    )
    parser.add_argument(
        '--epochs', 
        type=int, 
        default=3,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--batch-size', 
        type=int, 
        default=4,
        help='Training batch size'
    )
    parser.add_argument(
        '--learning-rate', 
        type=float, 
        default=2e-4,
        help='Learning rate'
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Limit number of training samples'
    )
    parser.add_argument(
        '--stats-only', 
        action='store_true',
        help='Only show training statistics'
    )
    parser.add_argument(
        '--list-adapters', 
        action='store_true',
        help='List available LoRA adapters'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'kairos_db',
        'user': 'kairos_user',
        'password': 'secure_password'
    }
    
    trainer = FineTuningTrainer(db_config, model_name=args.model)
    
    try:
        await trainer.initialize()
        logger.info("Database initialized successfully")
        
        if args.list_adapters:
            logger.info("📦 Available LoRA Adapters:")
            adapters = trainer.list_adapters()
            if adapters:
                for adapter in adapters:
                    logger.info(f"  • {adapter['adapter_name']} - {adapter['base_model']} ({adapter['training_samples']} samples)")
            else:
                logger.info("  No adapters found.")
            return
        
        # Get training statistics
        stats = await trainer.get_training_stats()
        logger.info(f"📊 Training Statistics:")
        logger.info(f"  Total samples: {stats['summary']['total_samples']}")
        logger.info(f"  Pending: {stats['summary']['pending']}")
        logger.info(f"  Labeled: {stats['summary']['labeled']}")
        logger.info(f"  Trained: {stats['summary']['trained']}")
        
        if args.stats_only:
            return
            
        # Fetch training data
        training_data = await trainer.fetch_training_data(limit=args.limit)
        
        if not training_data:
            logger.warning("❌ No training data available. Add some failed tasks first.")
            return
            
        logger.info(f"🎯 Found {len(training_data)} samples for training")
        
        # Confirm training
        print(f"\n🤖 Ready to fine-tune {args.model}")
        print(f"📊 Training samples: {len(training_data)}")
        print(f"🔄 Epochs: {args.epochs}")
        print(f"📦 Batch size: {args.batch_size}")
        print(f"📈 Learning rate: {args.learning_rate}")
        
        confirm = input("\n❓ Proceed with fine-tuning? (y/N): ")
        if confirm.lower() not in ['y', 'yes']:
            logger.info("❌ Fine-tuning cancelled.")
            return
            
        # Start fine-tuning
        logger.info("🚀 Starting fine-tuning process...")
        adapter_name = await trainer.fine_tune_model(
            training_data,
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate
        )
        
        if adapter_name:
            logger.info(f"✅ Fine-tuning completed successfully!")
            logger.info(f"🎯 Adapter name: {adapter_name}")
            logger.info(f"📁 Location: models/lora_adapters/{adapter_name}")
        else:
            logger.error("❌ Fine-tuning failed.")
            
    except KeyboardInterrupt:
        logger.info("⏹️  Fine-tuning interrupted by user.")
    except Exception as e:
        logger.error(f"❌ Fine-tuning failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        await trainer.close()

if __name__ == "__main__":
    asyncio.run(main())
