# domain/dataset_excel.py
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

            # --- PARTE A: Leer la hoja completa (sin encabezados iniciales) ---
            # pd.read_excel con header=None lee la hoja como un DataFrame donde los índices de fila y columna son 0-basados
            df_full_sheet = pd.read_excel(self.fuente, sheet_name=actual_sheet_name, header=None)
            
            # Eliminar filas completamente vacías para limpiar el DataFrame
            # Esto puede reindexar las filas, pero iloc siempre usa índices posicionales,
            # así que header_row_index y actual_nivel_general_row_index deben ser los índices resultantes.
            initial_rows_count = len(df_full_sheet)
            df_full_sheet.dropna(how='all', inplace=True)
            rows_after_dropna = len(df_full_sheet)
            print(f"DEBUG: Se eliminaron {initial_rows_count - rows_after_dropna} filas completamente vacías.")

            print("\n--- DEBUG: DataFrame de la hoja completa (primeras 15 filas) después de dropna(how='all') ---")
            print(df_full_sheet.head(15))
            print(df_full_sheet.info())
            print("---------------------------------------------------\n")

            # --- PARTE B: Encontrar el inicio de la tabla y la fila de "Nivel general" ---
            
            # Resetear el índice después de dropna para asegurar que los índices posicionales sean contiguos
            # Esto es CRÍTICO si dropna eliminó filas iniciales y luego estás usando iloc con índices originales.
            df_full_sheet.reset_index(drop=True, inplace=True)

            print("\n--- DEBUG: DataFrame después de reset_index (primeras 15 filas) ---")
            print(df_full_sheet.head(15))
            print(df_full_sheet.info())
            print("---------------------------------------------------\n")

            # Ahora, buscamos los índices en el DataFrame reindexado
            header_row_index_candidates = df_full_sheet[
                df_full_sheet.iloc[:, 0].astype(str).str.strip().str.lower() == target_region_title.lower()
            ].index

            if header_row_index_candidates.empty:
                raise ValueError(f"No se encontró la fila de encabezado de fechas para '{target_region_title}' en la hoja '{actual_sheet_name}'. Asegúrate que el nombre de la región en la columna A sea exacto y que las fechas estén en la misma fila que el nombre de la región.")
            
            header_row_index = header_row_index_candidates[0] 
            
            nivel_general_row_index_candidates = df_full_sheet[
                (df_full_sheet.iloc[:, 0].astype(str).str.strip().str.lower() == 'nivel general') & 
                (df_full_sheet.index > header_row_index) 
            ].index

            if nivel_general_row_index_candidates.empty:
                raise ValueError(f"No se encontró la fila 'Nivel general' para la región '{target_region_title}' después de la fila de encabezado de fechas.")
            
            actual_nivel_general_row_index = nivel_general_row_index_candidates[0]

            print(f"\n--- DEBUG: Índices de fila encontrados (después de reindexar) ---")
            print(f"header_row_index (fila de fechas esperada): {header_row_index}")
            print(f"actual_nivel_general_row_index (fila de variaciones esperada): {actual_nivel_general_row_index}")
            print("---------------------------------------------------\n")

            # --- PARTE C: Extraer y construir el DataFrame final correctamente ---
            
            # Extraer los datos brutos de la fila de fechas y variaciones
            # Excluimos la primera columna (columna 0) que contiene el texto de la región/nivel
            # Asegúrate de que los índices de columna son correctos.
            # Los valores de las fechas y variaciones comienzan en la columna 1 (segunda columna)
            
            # Vamos a intentar extraer directamente los valores como listas o arrays para evitar posibles reindexaciones de series
            # y luego convertirlos a series de Pandas con los índices correctos.
            
            fechas_raw_values = df_full_sheet.iloc[header_row_index, 1:].tolist()
            variaciones_raw_values = df_full_sheet.iloc[actual_nivel_general_row_index, 1:].tolist()

            # Aseguramos que ambas listas tengan la misma longitud
            min_len_raw = min(len(fechas_raw_values), len(variaciones_raw_values))
            fechas_raw_values = fechas_raw_values[:min_len_raw]
            variaciones_raw_values = variaciones_raw_values[:min_len_raw]

            # Convertir a Series para usar funcionalidades de Pandas, pero conservando los valores
            fechas_raw_series = pd.Series(fechas_raw_values).dropna()
            variaciones_raw_series = pd.Series(variaciones_raw_values).dropna()


            print("\n--- DEBUG: Información de fechas_raw_series ANTES de la conversión (extraída como lista) ---")
            if not fechas_raw_series.empty:
                print(f"fechas_raw_series.head():\n{fechas_raw_series.head()}")
                print(f"fechas_raw_series.dtype: {fechas_raw_series.dtype}")
                print(f"Tipo del primer valor de fechas_raw_series: {type(fechas_raw_series.iloc[0])}")
            else:
                print("fechas_raw_series está vacía.")
            print("\n--- DEBUG: Información de variaciones_raw_series ANTES de la conversión (extraída como lista) ---")
            if not variaciones_raw_series.empty:
                print(f"variaciones_raw_series.head():\n{variaciones_raw_series.head()}")
                print(f"variaciones_raw_series.dtype: {variaciones_raw_series.dtype}")
                print(f"Tipo del primer valor de variaciones_raw_series: {type(variaciones_raw_series.iloc[0])}")
            else:
                print("variaciones_raw_series está vacía.")
            print("---------------------------------------------------\n")

            # Alinear ambas series por sus índices (que ahora son 0-basados y contiguos si no se eliminaron NaNs en el medio)
            # Aunque ya las cortamos a la misma longitud, esta es una doble verificación
            min_len_aligned = min(len(fechas_raw_series), len(variaciones_raw_series))
            
            # Creamos un DataFrame con los valores alineados y luego limpiamos NaNs
            combined_df = pd.DataFrame({
                'fecha_val': fechas_raw_series.iloc[:min_len_aligned],
                'variacion_val': variaciones_raw_series.iloc[:min_len_aligned]
            })
            combined_df.dropna(inplace=True)


            if combined_df.empty:
                raise ValueError("No se encontraron pares válidos de fecha y variación después de la alineación y limpieza.")

            # Convertir la columna 'fecha_val' del DataFrame combinado a DatetimeIndex
            fechas_final = pd.to_datetime(combined_df['fecha_val'], errors='coerce', infer_datetime_format=True)

            if pd.isna(fechas_final).sum() > len(fechas_final) / 2 and combined_df['fecha_val'].apply(lambda x: isinstance(x, (int, float))).all():
                print("DEBUG: Parece que las fechas son números de serie de Excel en la columna 'fecha_val'. Intentando conversión con 'origin'.")
                fechas_final = pd.to_datetime(combined_df['fecha_val'], unit='D', origin='1899-12-30', errors='coerce')
            elif pd.isna(fechas_final).any():
                print("DEBUG: Algunas fechas no pudieron ser parseadas. Podría haber un formato inconsistente. Se eliminarán los NaT.")
            
            # Eliminar cualquier NaT que pudiera quedar en las fechas después de la conversión
            valid_indices = fechas_final.dropna().index
            fechas_final = fechas_final.loc[valid_indices]
            variaciones_final = pd.to_numeric(combined_df['variacion_val'].loc[valid_indices], errors='coerce').dropna()

            # Asegurarse de que las series finales estén alineadas y tengan la misma longitud
            if len(fechas_final) != len(variaciones_final):
                common_indices = fechas_final.index.intersection(variaciones_final.index)
                fechas_final = fechas_final.loc[common_indices]
                variaciones_final = variaciones_final.loc[common_indices]
            
            if fechas_final.empty or variaciones_final.empty:
                 raise ValueError("El DataFrame quedó vacío después de una limpieza exhaustiva de fechas y variaciones. Revisa los datos de la región seleccionada.")

            # Crear el DataFrame final con el DatetimeIndex correcto
            df_final_data = pd.DataFrame({
                'variacion_mensual': variaciones_final.values
            }, index=pd.DatetimeIndex(fechas_final)) # Aseguramos que el índice es DatetimeIndex
            
            # Ordenar por índice de fecha
            df_final_data.sort_index(inplace=True)

            print("\n--- DEBUG: DataFrame después de construir manualmente (variación mensual) ---")
            print(df_final_data.head())
            print(df_final_data.info())
            print("-------------------------------------------\n")

            # --- PARTE D: Calcular IPC Acumulado (Nivel General) ---
            ipc_acumulado = []
            ipc_actual = 100.0 # Base: Diciembre 2016 = 100

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