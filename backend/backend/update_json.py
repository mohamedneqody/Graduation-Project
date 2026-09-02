import json
with open('d:\\Graduation Project\\n8n_pharmacy_workflow_final.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for node in data['nodes']:
    if node['name'] == '3B. Send Email':
        # Add HTML and nicer text
        node['parameters']['text'] = '=مرحباً {{ $(\'1. Pull Pending Reminders\').item.json.customer_name }}،\n\nنود تذكيرك بأن دواءك ({{ $(\'1. Pull Pending Reminders\').item.json.drug_name }}) قد قارب على الانتهاء.\n\nلضمان عدم انقطاع العلاج، يرجى إعادة الطلب في أقرب وقت.\n\nمع تحيات صيدلية AI-COS'
        node['parameters']['html'] = '=<html><body dir="rtl" style="font-family: Tahoma, Arial, sans-serif; color: #333;"><div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e1e8ed; border-radius: 12px; background-color: #f9fbfd;"><div style="background-color: #2c3e50; padding: 15px; border-radius: 10px 10px 0 0; text-align: center;"><h2 style="color: #ffffff; margin: 0;">🏥 صيدلية AI-COS</h2></div><div style="padding: 20px; background-color: #ffffff; border-radius: 0 0 10px 10px;"><p style="font-size: 18px;">مرحباً <strong>{{ $(\'1. Pull Pending Reminders\').item.json.customer_name }}</strong>،</p><p style="font-size: 16px; line-height: 1.6;">نود تذكيرك بأن دواءك الموصوف:</p><div style="background-color: #e8f4f8; padding: 10px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: bold; color: #2980b9; margin: 15px 0;">{{ $(\'1. Pull Pending Reminders\').item.json.drug_name }}</div><p style="font-size: 16px; line-height: 1.6;">قد قارب على الانتهاء بناءً على سجلاتنا الذكية. لضمان عدم انقطاع العلاج والمحافظة على صحتك، نرجو منك تأكيد إعادة الطلب.</p><br><div style="text-align: center;"><a href="#" style="display: inline-block; background-color: #27ae60; color: #ffffff; text-decoration: none; padding: 12px 25px; border-radius: 6px; font-weight: bold; font-size: 16px;">🔄 إعادة الطلب الآن</a></div><hr style="border: none; border-top: 1px solid #eee; margin: 30px 0 15px 0;"><p style="font-size: 13px; color: #7f8c8d; text-align: center; margin: 0;">مع تحيات فريق الذكاء الاصطناعي في صيدلية AI-COS<br>نتمنى لك دوام الصحة والعافية 💙</p></div></div></body></html>'
        
        # Remove n8n attribution if possible
        if 'options' not in node['parameters']:
            node['parameters']['options'] = {}
        node['parameters']['options']['appendAttribution'] = False

with open('d:\\Graduation Project\\n8n_pharmacy_workflow_final.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print('Updated Email node successfully')
