import math
from langchain.tools import tool

@tool
def calculate_vacation_pay(monthly_salary: float, half_days_unused: float) -> int:
    """
    【僅限特休假使用】計算特休假工資。
    
    ⚠️ 使用限制：
    - 這個工具【僅限】用於計算「特休假」(Annual Leave / Special Vacation) 的工資
    - ❌ 禁止用於加班費、補休、或其他任何假別的計算
    
    📋 必要參數：
    - monthly_salary: 使用者的月薪（新台幣）
    - half_days_unused: 剩餘特休的半天數
    
    ⚠️ 重要規則：
    1. 如果使用者只是詢問「計算基準」或「規定」，請勿呼叫此工具，直接用文字回答政策即可
    2. 只有當使用者明確提供了「月薪」和「剩餘天數」時，才能呼叫此工具
    3. 如果缺少任何參數，請勿呼叫此工具，而是以文字回應詢問使用者提供缺少的數值
    4. 絕對禁止猜測或捏造數字（例如預設為 0、100 等）
    """
    daily_salary = math.ceil(monthly_salary / 30)
    pay = math.ceil(daily_salary * 0.5 * half_days_unused)
    return pay

@tool
def calculate_unused_overtime_pay(monthly_salary: int, half_days: float, remaining_minutes: float) -> float:
    """
    【僅限加班費使用】計算未休加班假的金額。
    
    ⚠️ 使用限制：
    - 這個工具【僅限】用於計算「加班費」或「補休轉換金額」(Overtime Pay)
    - ❌ 禁止用於特休假、病假、或其他任何假別的計算
    
    📋 必要參數：
    - monthly_salary: 使用者的月薪（新台幣）
    - half_days: 結算的半天數（加班時數轉換為半天）
    - remaining_minutes: 結算的分鐘數（不滿半天的零碎時數）
    
    ⚠️ 重要規則：
    1. 如果使用者只是詢問「計算基準」或「規定」，請勿呼叫此工具，直接用文字回答政策即可
    2. 只有當使用者明確提供了「月薪」和「加班時數/天數」時，才能呼叫此工具
    3. 如果缺少任何參數，請勿呼叫此工具，而是以文字回應詢問使用者提供缺少的數值
    4. 絕對禁止猜測或捏造數字（例如預設為 0、100 等）
    """
    # 1. 日薪 = 月薪 / 30天 (無條件進位到整數)
    daily_wage = math.ceil(monthly_salary / 30)
    
    # 2. 剩餘未轉換為分鐘數 = 結算半天數 X 4小時 X 60分鐘 + 結算分鐘數
    total_minutes = (half_days * 4 * 60) + remaining_minutes
    
    # 3. 金額 = 日薪 / 480分鐘 X 剩餘分鐘數 (無條件進位到整數)
    # 註：480分鐘即為 8小時
    final_amount = math.ceil((daily_wage / 480) * total_minutes)
    
    return final_amount