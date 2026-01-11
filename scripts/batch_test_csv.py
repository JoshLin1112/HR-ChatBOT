# python scripts/batch_test_csv.py --input QAtest.csv
import os
import sys
import pandas as pd
import uuid
import argparse
from tqdm import tqdm

# Ensure the project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.graph import GraphBuilder
from backend.rag_engine import RAGComponents
import logging

logger = logging.getLogger(__name__)

def run_batch_test(input_file, output_file, question_column):
    logger.info(f"Loading questions from: {input_file}")
    if not os.path.exists(input_file):
        logger.error(f"File {input_file} not found.")
        return

    df = pd.read_csv(input_file)
    if question_column not in df.columns:
        logger.error(f"Column '{question_column}' not found in CSV. Available columns: {list(df.columns)}")
        return

    logger.info("Initializing RAG Components and Graph...")
    rag = RAGComponents()
    builder = GraphBuilder(rag)
    graph = builder.build()

    results = []
    
    logger.info(f"Starting test on {len(df)} questions...")
    for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        question = row[question_column]
        
        # 使用隨機 uuid 作為 thread_id 確保歷史紀錄不會累積
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # 呼叫模型
            output = graph.invoke({"original_query": question}, config=config)
            model_answer = output.get("final_answer", "No answer generated.")
            retrieval_context = output.get("context", "No context retrieved.")
        except Exception as e:
            logger.error(f"Error processing question '{question}': {e}")
            model_answer = f"ERROR: {str(e)}"
            retrieval_context = "ERROR"
        
        # 記錄結果
        row_dict = row.to_dict()
        row_dict['model_answer'] = model_answer
        row_dict['retrieval_context'] = retrieval_context
        results.append(row_dict)

    # 儲存結果
    result_df = pd.DataFrame(results)
    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"Done! Results saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Systematic testing script for Chatbot using CSV.")
    parser.add_argument("--input", type=str, required=True, help="Path to the input CSV file.")
    parser.add_argument("--output", type=str, help="Path to the output CSV file (optional).")
    parser.add_argument("--column", type=str, default="question", help="The column name containing questions (default: 'question').")
    
    args = parser.parse_args()
    
    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_results{ext}"
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    run_batch_test(args.input, args.output, args.column)
