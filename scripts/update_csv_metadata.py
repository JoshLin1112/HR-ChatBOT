import pandas as pd
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "backend", "data", "QA617.csv")

def categorize_question(row):
    text = str(row['question']) + " " + str(row['answer'])
    
    # Priority matching
    if any(k in text for k in ['陪產', '陪產檢']):
        return 'paternity_leave'
    if any(k in text for k in ['產假', '流產', '小產', '安胎']):
        return 'maternity_leave'
    if any(k in text for k in ['產檢']):
        return 'prenatal_checkup_leave' # Separate or merge with maternity? Let's keep separate if distinct enough, but user asked about "similar but different".
                                         # Actually, let's keep it simple: "maternity_related" might be too broad. 
                                         # Let's use specific: maternity_leave (產假), paternity_leave (陪產), prenatal (產檢)
    if '病假' in text: 
        if '公傷' in text: return 'injury_leave'
        return 'sick_leave'
    if '喪假' in text: return 'funeral_leave'
    if '婚假' in text or '結婚' in text: return 'marriage_leave'
    if '特休' in text or '特別休假' in text: return 'annual_leave'
    if '事假' in text: return 'personal_leave'
    if '生理假' in text: return 'menstrual_leave'
    if '家庭照顧' in text: return 'family_care_leave'
    if '公假' in text: return 'official_leave'
    if '加班' in text or '補休' in text: return 'overtime'
    if '健保' in text or '保險' in text or '退休金' in text: return 'insurance_benefits'
    
    return 'other'

def main():
    logger.info(f"Reading data from {DATA_PATH}...")
    try:
        df = pd.read_csv(DATA_PATH)
        logger.info(f"Original columns: {df.columns.tolist()}")
        
        # Apply categorization
        df['category'] = df.apply(categorize_question, axis=1)
        
        print("\nCategory distribution:")
        print(df['category'].value_counts())
        
        # Save back
        df.to_csv(DATA_PATH, index=False, encoding='utf-8-sig')
        logger.info(f"Updated CSV saved to {DATA_PATH}")
        
    except Exception as e:
        logger.error(f"Error processing CSV: {e}")

if __name__ == "__main__":
    main()
