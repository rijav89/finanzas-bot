import re

with open('bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Remove globals
text = re.sub(r'datos_pendientes\s*=\s*\{\}\n', '', text)
text = re.sub(r'registro_manual_pendiente\s*=\s*\{\}\n', '', text)
text = re.sub(r'ingreso_pendiente\s*=\s*\{\}\n', '', text)
text = re.sub(r'pago_fijo_pendiente\s*=\s*\{\}\n', '', text)
text = re.sub(r'edicion_pendiente\s*=\s*\{\}\n', '', text)

# 2. Assigns
text = re.sub(r'ingreso_pendiente\[(?:telegram_id|tid)\]\s*=', r'context.user_data["ingreso_pendiente"] =', text)
text = re.sub(r'registro_manual_pendiente\[(?:telegram_id|tid)\]\s*=', r'context.user_data["registro_manual_pendiente"] =', text)
text = re.sub(r'datos_pendientes\[(?:telegram_id|tid)\]\s*=', r'context.user_data["datos_pendientes"] =', text)
text = re.sub(r'pago_fijo_pendiente\[(?:query\.from_user\.id|telegram_id|tid)\]\s*=', r'context.user_data["pago_fijo_pendiente"] =', text)
text = re.sub(r'edicion_pendiente\[(?:query\.from_user\.id|telegram_id|tid)\]\s*=', r'context.user_data["edicion_pendiente"] =', text)

# 3. Pops explicit handling
text = text.replace('datos = datos_pendientes.pop(telegram_id)', 'datos = context.user_data.pop("datos_pendientes")')

text = text.replace('datos_pendientes.pop(tid, None)', 'context.user_data.pop("datos_pendientes", None)')
text = text.replace('ingreso_pendiente.pop(tid, None)', 'context.user_data.pop("ingreso_pendiente", None)')
text = text.replace('pago_fijo_pendiente.pop(tid, None)', 'context.user_data.pop("pago_fijo_pendiente", None)')
text = text.replace('edicion_pendiente.pop(tid, None)', 'context.user_data.pop("edicion_pendiente", None)')
text = text.replace('registro_manual_pendiente.pop(tid, None)', 'context.user_data.pop("registro_manual_pendiente", None)')

text = text.replace('datos = ingreso_pendiente.pop(tid, {})', 'datos = context.user_data.pop("ingreso_pendiente", {})')
text = text.replace('datos = pago_fijo_pendiente.pop(tid, {})', 'datos = context.user_data.pop("pago_fijo_pendiente", {})')
text = text.replace('trans_id = edicion_pendiente.pop(tid)["id"]', 'trans_id = context.user_data.pop("edicion_pendiente", {})["id"]')
text = text.replace('pago_fijo_pendiente.pop(tid)', 'context.user_data.pop("pago_fijo_pendiente", None)')
text = text.replace('del registro_manual_pendiente[telegram_id]', 'context.user_data.pop("registro_manual_pendiente", None)')

# 4. Checks
text = text.replace('if telegram_id not in datos_pendientes:', 'if "datos_pendientes" not in context.user_data:')
text = text.replace('if telegram_id not in registro_manual_pendiente:', 'if "registro_manual_pendiente" not in context.user_data:')
text = text.replace('if tid in ingreso_pendiente:', 'if "ingreso_pendiente" in context.user_data:')
text = text.replace('if tid in edicion_pendiente:', 'if "edicion_pendiente" in context.user_data:')
text = text.replace('if tid in pago_fijo_pendiente:', 'if "pago_fijo_pendiente" in context.user_data:')
text = text.replace('if tid in registro_manual_pendiente:', 'if "registro_manual_pendiente" in context.user_data:')

# 5. Accesses
text = text.replace('datos = ingreso_pendiente[tid]', 'datos = context.user_data["ingreso_pendiente"]')
text = text.replace('datos = pago_fijo_pendiente[tid]', 'datos = context.user_data["pago_fijo_pendiente"]')

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(text)
    
print("Refactorizado exitosamente")
