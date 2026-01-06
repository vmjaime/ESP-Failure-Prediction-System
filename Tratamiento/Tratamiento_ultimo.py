import pandas as pd

# 1. Cargar el dataset limpio con campo ya corregido
file_path = r'C:\Users\Vìctor\OneDrive\Desktop\ESP_Project\df_completo_con_campo.xlsx'
df = pd.read_excel(file_path)

# 2. Verificación rápida de columnas actuales
print("Columnas originales:", df.columns.tolist())

# 3. Eliminar columnas innecesarias
columnas_a_eliminar = ['pozo', 'fecha']
df = df.drop(columns=[col for col in columnas_a_eliminar if col in df.columns])

# 4. Confirmar columnas finales
print("\nColumnas después de limpieza:", df.columns.tolist())

# 5. Guardar el archivo actualizado
output_path = r'C:\Users\Vìctor\OneDrive\Desktop\ESP_Project\df_final_limpio.xlsx'
df.to_excel(output_path, index=False)
print(f"\n✅ Dataset limpio guardado en: {output_path}")
