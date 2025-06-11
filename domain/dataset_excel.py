import pandas as pd
from domain.dataset import Dataset # Se respeta esta importación

class DatasetExcel(Dataset):
    def __init__(self, file_path):
        super().__init__(file_path)

    def cargar_datos(self, region_name):
        try:
            actual_sheet_name = "Variación mensual IPC Nacional"
            
            region_excel_titles = {
                "Total Nacional": "Total nacional",
                "Región GBA": "Región GBA",
                "Región Pampeana": "Región Pampeana",
                "Región Noroeste": "Región Noroeste",
                "Región Noreste": "Región Noreste",
                "Región Cuyo": "Región Cuyo",
                "Región Patagonia": "Región Patagonia"
            }
            
            target_region_title = region_excel_titles.get(region_name)
            if not target_region_title:
                raise ValueError(f"Región '{region_name}' no mapeada a un título de región válido en el Excel. Revisa 'region_excel_titles'.")

            # --- PARTE A: Leer la hoja completa (sin encabezados) ---
            df_full_sheet = pd.read_excel(self.fuente, sheet_name=actual_sheet_name, header=None)
            
            # Eliminar filas completamente vacías
            df_full_sheet.dropna(how='all', inplace=True)

            print("\n--- DEBUG: DataFrame de la hoja completa (primeras 15 filas) ---")
            print(df_full_sheet.head(15))
            print(df_full_sheet.info())
            print("---------------------------------------------------\n")

            # --- PARTE B: Encontrar el inicio de la tabla y la fila de "Nivel general" ---
            region_title_row_index = df_full_sheet[
                df_full_sheet.iloc[:, 0].astype(str).str.strip().str.lower() == target_region_title.lower()
            ].index

            if region_title_row_index.empty:
                raise ValueError(f"No se encontró el inicio de la tabla para '{target_region_title}' en la hoja '{actual_sheet_name}'. Asegúrate que el nombre de la región en la columna A sea exacto.")
            
            header_row_index = region_title_row_index[0]
            
            nivel_general_row_index = df_full_sheet[
                (df_full_sheet.iloc[:, 0].astype(str).str.strip().str.lower() == 'nivel general') & 
                (df_full_sheet.index > header_row_index) 
            ].index

            if nivel_general_row_index.empty:
                raise ValueError(f"No se encontró la fila 'Nivel general' para la región '{target_region_title}'.")
            
            actual_nivel_general_row_index = nivel_general_row_index[0]

            # --- PARTE C: Extraer y alinear las fechas y los datos de variación ---
            # Extraer los VALORES de las fechas (excluyendo la primera columna que es el texto 'Total Nacional')
            # y las variaciones.
            # Asegurarse de que tienen la misma longitud.
            fechas_list = df_full_sheet.iloc[header_row_index, 1:].dropna().tolist()
            variaciones_list = df_full_sheet.iloc[actual_nivel_general_row_index, 1:].dropna().tolist()

            # Asegurarse de que ambas listas tengan la misma longitud, tomando la menor.
            min_len = min(len(fechas_list), len(variaciones_list))
            fechas_list = fechas_list[:min_len]
            variaciones_list = variaciones_list[:min_len]

            # Crear el DataFrame directamente con las listas.
            temp_df = pd.DataFrame({
                'fecha_raw': fechas_list,
                'variacion_raw': variaciones_list
            })

            if temp_df.empty:
                raise ValueError("No se encontraron pares válidos de fecha y variación después de la extracción inicial. Verifique sus datos en Excel.")

            # Convertir la columna de fechas al tipo datetime
            # 'errors='coerce'' convertirá valores no convertibles a NaT (Not a Time), que luego se eliminarán.
            temp_df['fecha'] = pd.to_datetime(temp_df['fecha_raw'], errors='coerce')
            temp_df.dropna(subset=['fecha'], inplace=True) # Elimina filas con fechas inválidas
            
            # Convertir la columna de variaciones a numérico
            temp_df['variacion_mensual'] = pd.to_numeric(temp_df['variacion_raw'], errors='coerce')
            initial_rows_var = len(temp_df)
            temp_df.dropna(subset=['variacion_mensual'], inplace=True) # Elimina filas con variaciones inválidas

            if len(temp_df) < initial_rows_var:
                print(f"Advertencia: Se eliminaron {initial_rows_var - len(temp_df)} filas con valores no numéricos (o NaN) en la columna 'variacion_mensual' después de la conversión inicial.")
            
            if temp_df.empty:
                raise ValueError("El DataFrame quedó vacío después de eliminar filas con valores faltantes o incorrectos. Revisa los datos de la región seleccionada.")

            # Establecer 'fecha' como índice y ordenar
            df_final_data = temp_df.set_index('fecha')[['variacion_mensual']].sort_index()

            print("\n--- DEBUG: DataFrame después de construir manualmente (variación mensual) ---")
            print(df_final_data.head())
            print(df_final_data.info())
            print("-------------------------------------------\n")

            # --- PARTE D: Calcular IPC Acumulado (Nivel General) ---
            ipc_acumulado = []
            ipc_actual = 100.0 # Base: Diciembre 2016 = 100

            # Iteramos sobre las variaciones mensuales para calcular el IPC acumulado
            for variacion in df_final_data['variacion_mensual']:
                ipc_actual = ipc_actual * (1 + variacion / 100)
                ipc_acumulado.append(ipc_actual)

            df_final_data['ipc_valor'] = ipc_acumulado
            
            self.datos = df_final_data[['ipc_valor']] 
            
            print(f"Datos de Excel para '{region_name}' cargados y procesados exitosamente.")
            print("\n--- DEBUG: DataFrame FINAL procesado (IPC acumulado) ---")
            print(self.datos.head())
            print(self.datos.info())
            print("-------------------------------------------\n")
            
            if self.validar_datos():
                print("Datos validados exitosamente.") 
                self.transformar_datos() 
                print("Transformaciones básicas aplicadas.") 
            else:
                print("La validación de los datos del Excel falló.")

        except FileNotFoundError:
            print(f"Error: Archivo Excel no encontrado en {self.fuente}")
            self.datos = pd.DataFrame() 
        except ValueError as ve:
            print(f"Error al cargar datos desde Excel: {ve}. Revisa la estructura del Excel (encabezados, filas de regiones, formato de fechas, valores numéricos).")
            self.datos = pd.DataFrame()
        except Exception as e:
            print(f"Ocurrió un error inesperado al cargar datos de Excel: {e}")
            self.datos = pd.DataFrame()