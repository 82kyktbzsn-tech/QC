from classlesson_qc import check_abnormal_schedule_time
from data_loader import load_classlesson_excel
from labeling import apply_classlesson_standard_department


def main():
    df = load_classlesson_excel("data/classlesson.xlsx")
    result = apply_classlesson_standard_department(df)
    result = check_abnormal_schedule_time(result)

    output_path = "output/classlesson_labeled.xlsx"
    result.to_excel(output_path, index=False)

    print(f"classlesson 记录数：{len(result)} 行")
    print("标化部门分布：")
    print(result['标化部门'].value_counts(dropna=False).to_string())
    print(f"异常时间排课行数：{result['异常时间排课'].sum()} 行")
    print(f"标化完成，结果已保存至 {output_path}")


if __name__ == "__main__":
    main()
