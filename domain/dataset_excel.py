# domain/dataset_excel.py
import pandas as pd
from domain.dataset import Dataset

class DatasetExcel(Dataset):
    def __init__(self, file_path):
        super().__init__(file_path)

    def cargar_datos(self, region_name):
        try:
            # Ahora la hoja es siempre la misma
            actual_sheet_name = "Variación mensual IPC Nacional" 
            
            # Mapeo de nombres de región de entrada a los títulos dentro de la hoja
            # Asegúrate que estos nombres coincidan EXACTAMENTE con los que aparecen en la columna A de tu Excel
            region_excel_titles = {
                "Total Nacional": "Total País", # Suponiendo que el "Total Nacional" se llama "Total País" en Excel
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

            # --- PARTE A: Leer la hoja completa (o una parte grande) ---
            # Leemos la hoja entera o una parte lo suficientemente grande para contener todas las tablas.
            # No usamos 'header' aquí inicialmente porque necesitamos encontrar el encabezado de la tabla de la región dinámica.
            df_full_sheet = pd.read_excel(self.fuente, sheet_name=actual_sheet_name, header=None) # Leer sin encabezado
            
            # Eliminar filas completamente vacías (opcional, pero útil si hay muchas filas vacías)
            df_full_sheet.dropna(how='all', inplace=True)

            print("\n--- DEBUG: DataFrame de la hoja completa (primeras 10 filas) ---")
            print(df_full_sheet.head(10))
            print(df_full_sheet.info())
            print("---------------------------------------------------\n")

            # --- PARTE B: Encontrar el inicio de la tabla de la región deseada ---
            # Buscar la fila que contiene el título de la región (ej. "Región GBA")
            # Usamos .astype(str) para manejar NaNs o tipos mixtos y .str.strip().str.lower() para robustez.
            region_start_row_index = df_full_sheet[
                df_full_sheet.iloc[:, 0].astype(str).str.strip().str.lower() == target_region_title.lower()
            ].index

            if region_start_row_index.empty:
                raise ValueError(f"No se encontró el inicio de la tabla para '{target_region_title}' en la hoja '{actual_sheet_name}'. Asegúrate que el nombre de la región en la columna A sea exacto.")
            
            # Asumimos que la tabla de la región comienza JUSTO después de esta fila de título.
            # Y que los encabezados de los meses están en la misma fila del título de la región.
            # Y la fila de "Nivel general" está 3 filas más abajo.

            # Fila donde están los nombres de los meses (ej. ene-17, feb-17)
            # Según tu imagen, los meses están en la misma fila que "Región GBA" (Fila 7 en imagen_aebe5c.png, Fila 36 en image_b8abb9.png)
            # Esto significa que el encabezado real de los meses es la fila donde encontramos el título de la región.
            header_row_for_months = region_start_row_index[0] # Convertir a índice de fila de Python

            # Fila donde está la categoría "Nivel general" (parece estar 3 filas más abajo del título de la región)
            # Si "Región GBA" está en la fila 36 y "Nivel general" en la 39, entonces es 3 filas más abajo.
            nivel_general_data_row_offset = 3 # Desplazamiento desde la fila del encabezado de los meses

            # --- PARTE C: Leer la tabla específica de la región con encabezados correctos ---
            # Leemos el Excel de nuevo, pero ahora especificando el 'header' dinámicamente.
            df_region_table = pd.read_excel(
                self.fuente,
                sheet_name=actual_sheet_name,
                header=header_row_for_months # Usar la fila donde están los meses como encabezado
            )
            
            # Después de leer con el header, la primera columna será 'Unnamed: 0' o similar
            # y contendrá los nombres de las categorías como "Nivel general", "Alimentos...", etc.
            
            # **NUEVO: Limpiar nombres de columnas después de la lectura con header.**
            # Esto es crucial para acceder a las columnas por un nombre predecible.
            # Los nombres de los meses (ene-17, feb-17, etc.) se convertirán a snake_case.
            df_region_table.columns = df_region_table.columns.astype(str).str.strip().str.lower().str.replace(' ', '_').str.replace('%', '_pct')

            # Eliminar filas completamente vacías (en caso de que queden, o si la lectura con header introdujo más)
            df_region_table.dropna(how='all', inplace=True)
            if df_region_table.empty:
                raise ValueError("El DataFrame de la tabla de la región quedó vacío. Revisa el 'header' y la estructura.")

            # --- DEBUGGING: DataFrame de la tabla de la región (después de header dinámico y limpieza de columnas) ---
            print(f"\n--- DEBUG: DataFrame de la tabla '{target_region_title}' (después de leer con header dinámico y limpiar cols) ---")
            print(f"Columnas detectadas: {df_region_table.columns.tolist()}")
            print(df_region_table.head())
            print(df_region_table.info())
            print("---------------------------------------------------\n")


            # Identificar la columna que contiene "Nivel general" y otras categorías.
            # Asumimos que es la primera columna después de la lectura con header.
            category_col_name = df_region_table.columns[0] 

            # Filtrar para la fila "Nivel general" DENTRO de esta tabla de región
            df_nivel_general_row = df_region_table[
                df_region_table[category_col_name].astype(str).str.strip().str.lower() == 'nivel general'
            ].copy()

            if df_nivel_general_row.empty:
                raise ValueError(f"No se encontró la fila 'Nivel general' dentro de la tabla de '{target_region_title}'.")
            
            # --- PARTE D: Transformar de formato ancho a formato largo (melt) ---
            
            # Obtener los nombres de las columnas que representan los meses (todas excepto la primera, que es la categoría)
            month_columns = [col for col in df_nivel_general_row.columns if col != category_col_name]

            # Usar pd.melt para transformar las columnas de meses en filas
            df_long = df_nivel_general_row.melt(id_vars=[category_col_name], 
                                                value_vars=month_columns, 
                                                var_name='fecha_str', # Nombre temporal para la columna de meses (string)
                                                value_name='variacion_mensual')

            # --- DEBUGGING: Después de melt ---
            print("\n--- DEBUG: DataFrame después de melt ---")
            print(df_long.head())
            print(df_long.info())
            print("-------------------------------------------\n")

            # --- PARTE E: Procesar columna de Fecha y Variación ---

            # Convertir la columna 'fecha_str' a tipo datetime
            # El formato '%b-%y' es para 'ene-17', 'feb-17', etc. Si tu Excel usa otro, ajústalo.
            df_long['fecha'] = pd.to_datetime(df_long['fecha_str'], format='%b-%y', errors='coerce') 
            df_long.dropna(subset=['fecha'], inplace=True) # Eliminar filas donde la conversión de fecha falló
            
            # Convertir 'variacion_mensual' a numérico.
            df_long['variacion_mensual'] = pd.to_numeric(df_long['variacion_mensual'], errors='coerce')
            
            # Como confirmaste que no hay NaNs en la columna de Nivel General para el rango relevante,
            # si aparece un NaN aquí, es que el valor original no era numérico y debe ser descartado.
            initial_rows_var = len(df_long)
            df_long.dropna(subset=['variacion_mensual'], inplace=True)
            if len(df_long) < initial_rows_var:
                print(f"Advertencia: Se eliminaron {initial_rows_var - len(df_long)} filas con valores no numéricos (o NaN) en la columna 'variacion_mensual'.")
            if df_long.empty:
                 raise ValueError("El DataFrame quedó vacío después de eliminar filas con valores faltantes en la columna de variación. Revisa los datos de la región seleccionada.")

            # Establecer 'fecha' como índice del DataFrame final
            df_long.set_index('fecha', inplace=True)
            df_long.sort_index(inplace=True)

            # --- PARTE F: Calcular IPC Acumulado (Nivel General) ---
            # Asumo que tu "Nivel General" de la imagen es la variación en porcentaje (ej. 1.8 para 1.8%).
            
            # Convertir la variación a factor multiplicador (ej. 5% -> 1.05)
            df_long['factor_multiplicador'] = 1 + (df_long['variacion_mensual'] / 100)
            
            # Establecer el IPC inicial (ej. 100 para la primera fecha disponible)
            # Esto establece el IPC de Ene-17 en 100 y acumula a partir de ahí.
            ipc_inicial_value = 100.0 
            
            # Calcular el IPC acumulado usando la multiplicación acumulada (.cumprod())
            df_long['ipc_acumulado'] = ipc_inicial_value * df_long['factor_multiplicador'].cumprod()
            
            # Asignar el DataFrame final procesado a self.datos
            self.datos = df_long[['ipc_acumulado']].rename(columns={'ipc_acumulado': 'ipc_valor'})
            
            print(f"Datos de Excel para '{region_name}' cargados y procesados exitosamente.")
            print("\n--- DEBUG: DataFrame FINAL procesado ---")
            print(self.datos.head())
            print(self.datos.info())
            print("-------------------------------------------\n")
            
            # Llama a la validación y transformación de la clase base
            if self.validar_datos():
                self.transformar_datos()
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