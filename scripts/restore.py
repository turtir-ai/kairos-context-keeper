#!/usr/bin/env python3
"""
Kairos Restore System
Automated restore script for Neo4j and Qdrant databases from backups
"""

import os
import sys
import asyncio
import tarfile
import shutil
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

try:
    from memory.neo4j_integration import Neo4jIntegration
    from memory.qdrant_integration import QdrantIntegration
    NEO4J_AVAILABLE = True
    QDRANT_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Database imports failed: {e}")
    NEO4J_AVAILABLE = False 
    QDRANT_AVAILABLE = False

class KairosRestoreManager:
    """Manages restore operations for Kairos databases"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("restore.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connections
        self.neo4j = None 
        self.qdrant = None
        
        if NEO4J_AVAILABLE:
            try:
                self.neo4j = Neo4jIntegration()
                self.logger.info("✅ Neo4j connection initialized")
            except Exception as e:
                self.logger.warning(f"Neo4j connection failed: {e}")
        
        if QDRANT_AVAILABLE:
            try:
                self.qdrant = QdrantIntegration()
                self.logger.info("✅ Qdrant connection initialized")
            except Exception as e:
                self.logger.warning(f"Qdrant connection failed: {e}")
    
    async def restore_from_backup(self, backup_name: str, components: Optional[List[str]] = None) -> Dict[str, Any]:
        """Restore from a backup archive"""
        self.logger.info(f"🔄 Starting restore from backup: {backup_name}")
        
        restore_manifest = {
            "backup_name": backup_name,
            "restore_started_at": datetime.now().isoformat(),
            "components_restored": [],
            "status": "in_progress",
            "warnings": []
        }
        
        try:
            # 1. Extract backup archive
            backup_path = await self._extract_backup_archive(backup_name)
            if not backup_path:
                raise Exception(f"Failed to extract backup: {backup_name}")
            
            # 2. Load backup manifest
            manifest_file = backup_path / "backup_manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    backup_manifest = json.load(f)
                restore_manifest["backup_info"] = backup_manifest
            else:
                self.logger.warning("⚠️ No backup manifest found, proceeding with best effort")
                restore_manifest["warnings"].append("No backup manifest found")
            
            # 3. Restore components
            available_components = ["neo4j", "qdrant", "project", "config"]
            components_to_restore = components or available_components
            
            for component in components_to_restore:
                component_path = backup_path / component
                if component_path.exists():
                    result = await self._restore_component(component, component_path)
                    restore_manifest["components_restored"].append(result)
                else:
                    self.logger.warning(f"⚠️ Component {component} not found in backup")
                    restore_manifest["warnings"].append(f"Component {component} not found")
            
            # 4. Cleanup temporary files
            shutil.rmtree(backup_path)
            
            restore_manifest["status"] = "completed"
            restore_manifest["restore_completed_at"] = datetime.now().isoformat()
            
            self.logger.info(f"✅ Restore completed: {backup_name}")
            
            return restore_manifest
            
        except Exception as e:
            restore_manifest["status"] = "failed"
            restore_manifest["error"] = str(e)
            self.logger.error(f"❌ Restore failed: {e}")
            return restore_manifest
    
    async def _extract_backup_archive(self, backup_name: str) -> Optional[Path]:
        """Extract backup archive to temporary directory"""
        # Find backup file
        backup_file = None
        possible_names = [
            self.backup_dir / f"{backup_name}.tar.gz",
            self.backup_dir / f"{backup_name}",
            self.backup_dir / backup_name
        ]
        
        for possible_file in possible_names:
            if possible_file.exists():
                backup_file = possible_file
                break
        
        if not backup_file:
            self.logger.error(f"❌ Backup file not found: {backup_name}")
            return None
        
        # Create temporary extraction directory
        temp_dir = self.backup_dir / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"🔄 Extracting backup archive: {backup_file.name}")
        
        try:
            if backup_file.suffix == '.gz':
                with tarfile.open(backup_file, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Find extracted directory
                extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir()]
                if extracted_dirs:
                    return extracted_dirs[0]
                else:
                    return temp_dir
            else:
                # Assume it's already an extracted directory
                return backup_file
                
        except Exception as e:
            self.logger.error(f"❌ Failed to extract backup: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
    
    async def _restore_component(self, component: str, component_path: Path) -> Dict[str, Any]:
        """Restore a specific component"""
        self.logger.info(f"🔄 Restoring component: {component}")
        
        component_result = {
            "component": component,
            "status": "in_progress",
            "started_at": datetime.now().isoformat()
        }
        
        try:
            if component == "neo4j":
                result = await self._restore_neo4j(component_path)
            elif component == "qdrant":
                result = await self._restore_qdrant(component_path)
            elif component == "project":
                result = await self._restore_project_files(component_path)
            elif component == "config":
                result = await self._restore_configuration(component_path)
            else:
                result = {"status": "skipped", "reason": "Unknown component"}
            
            component_result.update(result)
            component_result["completed_at"] = datetime.now().isoformat()
            
            if result.get("status") == "completed":
                self.logger.info(f"✅ Component {component} restored successfully")
            else:
                self.logger.warning(f"⚠️ Component {component} restore completed with issues")
            
        except Exception as e:
            component_result.update({
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now().isoformat()
            })
            self.logger.error(f"❌ Component {component} restore failed: {e}")
        
        return component_result
    
    async def _restore_neo4j(self, backup_path: Path) -> Dict[str, Any]:
        """Restore Neo4j knowledge graph from backup"""
        self.logger.info("🔄 Restoring Neo4j knowledge graph...")
        
        try:
            # Load backup files
            nodes_file = backup_path / "nodes.json"
            relationships_file = backup_path / "relationships.json"
            schema_file = backup_path / "schema.json"
            
            restore_stats = {
                "nodes_restored": 0,
                "relationships_restored": 0,
                "schema_restored": False
            }
            
            # Restore nodes
            if nodes_file.exists():
                with open(nodes_file, 'r') as f:
                    nodes_data = json.load(f)
                
                if self.neo4j and hasattr(self.neo4j, 'execute_query'):
                    # Clear existing data (WARNING: This deletes all data!)
                    await self._confirm_neo4j_clear()
                    await self.neo4j.execute_query("MATCH (n) DETACH DELETE n")
                    
                    # Restore nodes
                    for node in nodes_data:
                        try:
                            node_props = node.get("properties", {})
                            labels = ":".join(node.get("labels", ["Node"]))
                            
                            # Create node query
                            query = f"CREATE (n:{labels} $props)"
                            await self.neo4j.execute_query(query, {"props": node_props})
                            restore_stats["nodes_restored"] += 1
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to restore node {node.get('node_id')}: {e}")
                
                else:
                    # Mock restore for testing
                    restore_stats["nodes_restored"] = len(nodes_data)
                    self.logger.info(f"🔄 Mock restore: {len(nodes_data)} nodes")
            
            # Restore relationships
            if relationships_file.exists():
                with open(relationships_file, 'r') as f:
                    relationships_data = json.load(f)
                
                if self.neo4j and hasattr(self.neo4j, 'execute_query'):
                    for rel in relationships_data:
                        try:
                            rel_type = rel.get("type", "RELATES_TO")
                            rel_props = rel.get("properties", {})
                            start_node_id = rel.get("start_node")
                            end_node_id = rel.get("end_node")
                            
                            # Create relationship query (simplified)
                            query = f"""
                            MATCH (a), (b) 
                            WHERE a.id = $start_id AND b.id = $end_id
                            CREATE (a)-[r:{rel_type} $props]->(b)
                            """
                            await self.neo4j.execute_query(query, {
                                "start_id": start_node_id,
                                "end_id": end_node_id,
                                "props": rel_props
                            })
                            restore_stats["relationships_restored"] += 1
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to restore relationship {rel.get('rel_id')}: {e}")
                
                else:
                    # Mock restore for testing
                    restore_stats["relationships_restored"] = len(relationships_data)
                    self.logger.info(f"🔄 Mock restore: {len(relationships_data)} relationships")
            
            # Restore schema
            if schema_file.exists():
                with open(schema_file, 'r') as f:
                    schema_data = json.load(f)
                
                if self.neo4j and hasattr(self.neo4j, 'execute_query'):
                    # Create indexes
                    for index in schema_data.get("indexes", []):
                        try:
                            query = f"CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.{index})"
                            await self.neo4j.execute_query(query)
                        except Exception as e:
                            self.logger.warning(f"Failed to create index {index}: {e}")
                    
                    # Create constraints
                    for constraint in schema_data.get("constraints", []):
                        try:
                            if "unique" in constraint:
                                field = constraint.replace("unique_", "")
                                query = f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.{field} IS UNIQUE"
                                await self.neo4j.execute_query(query)
                        except Exception as e:
                            self.logger.warning(f"Failed to create constraint {constraint}: {e}")
                
                restore_stats["schema_restored"] = True
            
            return {
                "status": "completed",
                "stats": restore_stats
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _restore_qdrant(self, backup_path: Path) -> Dict[str, Any]:
        """Restore Qdrant vector database from backup"""
        self.logger.info("🔄 Restoring Qdrant vector database...")
        
        try:
            # Load metadata
            metadata_file = backup_path / "metadata.json"
            if not metadata_file.exists():
                return {"status": "failed", "error": "No Qdrant metadata found"}
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            collections = metadata.get("collections", [])
            restore_stats = {
                "collections_restored": 0,
                "vectors_restored": 0
            }
            
            for collection_name in collections:
                collection_file = backup_path / f"{collection_name}.json"
                if collection_file.exists():
                    result = await self._restore_qdrant_collection(collection_name, collection_file)
                    if result.get("status") == "completed":
                        restore_stats["collections_restored"] += 1
                        restore_stats["vectors_restored"] += result.get("vectors_restored", 0)
            
            return {
                "status": "completed",
                "stats": restore_stats
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _restore_qdrant_collection(self, collection_name: str, collection_file: Path) -> Dict[str, Any]:
        """Restore a specific Qdrant collection"""
        try:
            with open(collection_file, 'r') as f:
                vectors_data = json.load(f)
            
            if self.qdrant and hasattr(self.qdrant, 'upsert_vectors'):
                # Delete existing collection
                await self._confirm_qdrant_clear(collection_name)
                try:
                    await self.qdrant.delete_collection(collection_name)
                except:
                    pass  # Collection might not exist
                
                # Create new collection
                await self.qdrant.create_collection(
                    collection_name, 
                    vector_size=384,  # Default size
                    distance="Cosine"
                )
                
                # Restore vectors in batches
                batch_size = 100
                restored_count = 0
                
                for i in range(0, len(vectors_data), batch_size):
                    batch = vectors_data[i:i + batch_size]
                    
                    # Format for Qdrant
                    points = []
                    for vector_data in batch:
                        points.append({
                            "id": vector_data.get("id"),
                            "vector": vector_data.get("vector"),
                            "payload": vector_data.get("metadata", {})
                        })
                    
                    await self.qdrant.upsert_vectors(collection_name, points)
                    restored_count += len(batch)
                
                return {
                    "status": "completed",
                    "vectors_restored": restored_count
                }
            
            else:
                # Mock restore for testing
                return {
                    "status": "completed",
                    "vectors_restored": len(vectors_data)
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _restore_project_files(self, backup_path: Path) -> Dict[str, Any]:
        """Restore project files from backup"""
        self.logger.info("🔄 Restoring project files...")
        
        try:
            restored_files = []
            
            # Restore individual files to project root
            for file_path in backup_path.iterdir():
                if file_path.is_file():
                    dest_path = Path(file_path.name)
                    
                    # Ask for confirmation before overwriting important files
                    if dest_path.exists():
                        if not await self._confirm_overwrite(str(dest_path)):
                            self.logger.info(f"⏭️ Skipped: {dest_path}")
                            continue
                    
                    shutil.copy2(file_path, dest_path)
                    restored_files.append(str(dest_path))
                    self.logger.info(f"📁 Restored: {dest_path}")
                
                # Restore directories
                elif file_path.is_dir():
                    dest_path = Path(file_path.name)
                    
                    if dest_path.exists():
                        if not await self._confirm_overwrite(str(dest_path)):
                            self.logger.info(f"⏭️ Skipped directory: {dest_path}")
                            continue
                        shutil.rmtree(dest_path)
                    
                    shutil.copytree(file_path, dest_path)
                    restored_files.append(str(dest_path) + "/")
                    self.logger.info(f"📁 Restored directory: {dest_path}")
            
            return {
                "status": "completed",
                "files_restored": restored_files,
                "file_count": len(restored_files)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _restore_configuration(self, backup_path: Path) -> Dict[str, Any]:
        """Restore system configuration from backup"""
        self.logger.info("🔄 Restoring configuration...")
        
        try:
            config_files = []
            
            # Restore config files to configs/ directory
            configs_dir = Path("configs")
            configs_dir.mkdir(exist_ok=True)
            
            for config_file in backup_path.iterdir():
                if config_file.is_file() and config_file.suffix == '.json':
                    dest_path = configs_dir / f"restored_{config_file.name}"
                    shutil.copy2(config_file, dest_path)
                    config_files.append(str(dest_path))
                    self.logger.info(f"⚙️ Restored config: {dest_path}")
            
            return {
                "status": "completed",
                "config_files": config_files,
                "file_count": len(config_files)
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    async def _confirm_neo4j_clear(self) -> bool:
        """Confirm Neo4j database clearing"""
        if os.getenv("KAIROS_AUTO_CONFIRM") == "true":
            return True
        
        print("⚠️  WARNING: This will delete ALL existing Neo4j data!")
        response = input("Continue? (yes/no): ").lower().strip()
        return response in ["yes", "y"]
    
    async def _confirm_qdrant_clear(self, collection_name: str) -> bool:
        """Confirm Qdrant collection clearing"""
        if os.getenv("KAIROS_AUTO_CONFIRM") == "true":
            return True
        
        print(f"⚠️  WARNING: This will delete ALL data in Qdrant collection '{collection_name}'!")
        response = input("Continue? (yes/no): ").lower().strip()
        return response in ["yes", "y"]
    
    async def _confirm_overwrite(self, file_path: str) -> bool:
        """Confirm file overwriting"""
        if os.getenv("KAIROS_AUTO_CONFIRM") == "true":
            return True
        
        print(f"⚠️  File '{file_path}' already exists.")
        response = input("Overwrite? (yes/no): ").lower().strip()
        return response in ["yes", "y"]
    
    def list_available_backups(self) -> List[Dict[str, Any]]:
        """List all available backup archives"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_file in self.backup_dir.glob("kairos_backup_*.tar.gz"):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.stem,
                "file": backup_file.name,
                "size_mb": stat.st_size / 1024 / 1024,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "path": str(backup_file)
            })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        
        return backups
    
    async def validate_backup(self, backup_name: str) -> Dict[str, Any]:
        """Validate a backup archive without restoring"""
        self.logger.info(f"🔍 Validating backup: {backup_name}")
        
        validation_result = {
            "backup_name": backup_name,
            "valid": True,
            "issues": [],
            "components": [],
            "validation_time": datetime.now().isoformat()
        }
        
        try:
            # Extract backup for validation
            backup_path = await self._extract_backup_archive(backup_name)
            if not backup_path:
                validation_result["valid"] = False
                validation_result["issues"].append("Failed to extract backup archive")
                return validation_result
            
            # Check manifest
            manifest_file = backup_path / "backup_manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r') as f:
                    manifest = json.load(f)
                validation_result["manifest"] = manifest
                
                if manifest.get("status") != "completed":
                    validation_result["issues"].append("Backup was not completed successfully")
            else:
                validation_result["issues"].append("No backup manifest found")
            
            # Check components
            expected_components = ["neo4j", "qdrant", "project", "config"]
            for component in expected_components:
                component_path = backup_path / component
                if component_path.exists():
                    validation_result["components"].append({
                        "name": component,
                        "status": "present",
                        "file_count": len(list(component_path.rglob("*")))
                    })
                else:
                    validation_result["components"].append({
                        "name": component,
                        "status": "missing"
                    })
                    validation_result["issues"].append(f"Component {component} missing")
            
            # Cleanup
            shutil.rmtree(backup_path)
            
            if validation_result["issues"]:
                validation_result["valid"] = False
            
            self.logger.info(f"✅ Backup validation completed: {'Valid' if validation_result['valid'] else 'Invalid'}")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["issues"].append(f"Validation error: {str(e)}")
            self.logger.error(f"❌ Backup validation failed: {e}")
        
        return validation_result


async def main():
    """Main restore script function"""
    parser = argparse.ArgumentParser(description="Kairos Restore System")
    parser.add_argument("backup_name", nargs="?", help="Name of backup to restore")
    parser.add_argument("--list", action="store_true", help="List available backups")
    parser.add_argument("--validate", help="Validate a backup without restoring")
    parser.add_argument("--components", nargs="+", help="Specific components to restore", 
                       choices=["neo4j", "qdrant", "project", "config"])
    parser.add_argument("--backup-dir", default="backups", help="Backup directory path")
    parser.add_argument("--auto-confirm", action="store_true", help="Auto-confirm all prompts")
    
    args = parser.parse_args()
    
    # Set environment variable for auto-confirmation
    if args.auto_confirm:
        os.environ["KAIROS_AUTO_CONFIRM"] = "true"
    
    # Initialize restore manager
    restore_manager = KairosRestoreManager(args.backup_dir)
    
    if args.list:
        # List available backups
        backups = restore_manager.list_available_backups()
        if backups:
            print("\n📦 Available Backups:")
            print("-" * 80)
            for backup in backups:
                print(f"🗃️  {backup['name']}")
                print(f"   File: {backup['file']}")
                print(f"   Size: {backup['size_mb']:.2f} MB")
                print(f"   Created: {backup['created_at']}")
                print()
        else:
            print("No backups found.")
        return
    
    if args.validate:
        # Validate backup
        validation_result = await restore_manager.validate_backup(args.validate)
        print(f"\n🔍 Backup Validation: {args.validate}")
        print("-" * 60)
        print(f"Valid: {'✅ Yes' if validation_result['valid'] else '❌ No'}")
        
        if validation_result["issues"]:
            print("\nIssues found:")
            for issue in validation_result["issues"]:
                print(f"  ⚠️  {issue}")
        
        print("\nComponents:")
        for component in validation_result["components"]:
            status_icon = "✅" if component["status"] == "present" else "❌"
            print(f"  {status_icon} {component['name']}: {component['status']}")
        
        return
    
    if not args.backup_name:
        print("❌ Error: backup_name is required")
        print("Use --list to see available backups")
        sys.exit(1)
    
    # Perform restore
    print(f"🚀 Starting restore from backup: {args.backup_name}")
    
    if not args.auto_confirm:
        print("\n⚠️  WARNING: This operation will overwrite existing data!")
        response = input("Continue with restore? (yes/no): ").lower().strip()
        if response not in ["yes", "y"]:
            print("Restore cancelled.")
            return
    
    restore_result = await restore_manager.restore_from_backup(
        args.backup_name, 
        components=args.components
    )
    
    if restore_result["status"] == "completed":
        print("\n✅ Restore completed successfully!")
        print(f"🔧 Components restored: {len(restore_result['components_restored'])}")
        
        for component in restore_result["components_restored"]:
            status_icon = "✅" if component["status"] == "completed" else "⚠️"
            print(f"   {status_icon} {component['component']}")
        
        if restore_result.get("warnings"):
            print("\nWarnings:")
            for warning in restore_result["warnings"]:
                print(f"  ⚠️  {warning}")
    
    else:
        print(f"\n❌ Restore failed: {restore_result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
