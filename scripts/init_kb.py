import os
import sys
import logging

# Ensure project root is in path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from src.core.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Knowledge Base for Phase 3...")
    
    try:
        kb = KnowledgeBase()
        
        # Clear existing to avoid duplicates/stale data (Clean Slate Protocol)
        logger.info("Clearing existing collection...")
        kb.clear()

        # Ingest Policy
        policy_path_candidates = [
            os.path.join(project_root, "doc", "01_execution", "policies", "credit_policy_v1.md"),
            os.path.join(project_root, "doc", "policies", "credit_policy_v1.md"),
        ]
        policy_path = next((p for p in policy_path_candidates if os.path.exists(p)), None)
        if policy_path:
            kb.ingest_document(policy_path)
            logger.info(f"Policy ingested successfully from {policy_path}.")
        else:
            logger.warning("Policy file not found. Skipping KB policy ingest.")
            
    except Exception as e:
        logger.error(f"Knowledge Base initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
