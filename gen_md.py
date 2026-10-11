output_path = r"D:\Graduation Project\ملفات 11\10_الشات_بوت_والوكلاء_والرؤية_الحاسوبية.md"
with open(output_path, "w", encoding="utf-8") as out:
    out.write(content)
print(len(content.splitlines()))
