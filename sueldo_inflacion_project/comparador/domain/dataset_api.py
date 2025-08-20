import requests
import pandas as pd
from .dataset import Dataset
from urllib.parse import urlencode


class DatasetAPI(Dataset):
    """
    Clase para obtener datos de series de tiempo del INDEC a través de la API
    de datos.gob.ar, especialmente el Índice de Precios al Consumidor (IPC).
    """
    # URL base para la API de series de tiempo del Ministerio de Economía
    BASE_URL = "https://apis.datos.gob.ar/series/api/series"

    # ID de la serie para el Índice de Precios al Consumidor (IPC) - Nivel General Nacional.
    # Este es el ID comúnmente utilizado en la API de datos.gob.ar para el IPC Nacional.
    IPC_NATIONAL_ID = "101.1_I2NG_2016_M_22"  

    # NOTA: En la imagen del JSON que mostraste anteriormente, aparecía el ID "101.1_T2NC_2016_M_22"
    # que corresponde al Índice de Precios al Consumidor GBA (Gran Buenos Aires).
    # Si quisieras usar el IPC GBA en lugar del Nacional, deberías cambiar IPC_NATIONAL_ID a este.
    # IPC_GBA_ID = "101.1_T2NC_2016_M_22"

    def __init__(self):
        # Inicializamos la clase base. La 'fuente' (URL completa) se construirá en cargar_datos.
        super().__init__(None) # Pasamos None ya que la URL se define dinámicamente

    def cargar_datos(self, series_ids: list[str], start_date: str, end_date: str = None):  # type: ignore
        """
        Carga datos de series de tiempo del INDEC (o cualquier serie de datos.gob.ar)
        en formato JSON.

        Args:
            series_ids (list[str]): Una lista de IDs de las series a consultar.
                                     Ej: ["101.1_I2NG_2016_M_22"] para el IPC Nacional.
            start_date (str): Fecha de inicio para la consulta en formato 'YYYY-MM-DD'.
            end_date (str, optional): Fecha de fin para la consulta en formato 'YYYY-MM-DD'.
                                       Si es None, la API traerá datos hasta la fecha más reciente.
        """
        # Parámetros para la consulta a la API
        params = {
            "ids": ",".join(series_ids),  # Une los IDs con comas para la URL
            "start_date": start_date,
            "format": "json"              # Solicitamos la respuesta en formato JSON
        }
        if end_date:
            params["end_date"] = end_date

        # Construir la URL completa con los parámetros codificados
        self.fuente = f"{self.BASE_URL}?{urlencode(params)}"
        print(f"URL de la API construida: {self.fuente}")

        try:
            print(f"Intentando obtener datos de: {self.fuente}")
            response = requests.get(self.fuente)
            response.raise_for_status()  # Lanza una excepción para códigos de estado HTTP 4xx/5xx

            data = response.json()

            # La API de datos.gob.ar devuelve las series de tiempo bajo la clave 'data'
            # Simplificamos la condición para solo verificar que 'data' exista y no esté vacía.
            if 'data' in data and data['data']: 
                
                # Columnas esperadas: 'fecha' y el ID de la serie solicitado.
                # Usamos la lista de series_ids pasadas a la función para nombrar las columnas.
                # Esto es más robusto si la estructura de 'series' o 'meta' en la respuesta JSON varía.
                column_names = ['fecha'] + series_ids
                
                df = pd.DataFrame(data['data'], columns=column_names)

                # Convertir la columna 'fecha' a tipo datetime
                df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce') # Añadido errors='coerce' para robustez

                # --- INICIO DE LAS MODIFICACIONES NECESARIAS ---
                # Establecer 'fecha' como el índice del DataFrame
                # y asegurar que sea DatetimeIndex con el primer día del mes
                df = df.set_index('fecha').dropna(subset=[series_ids[0]]) # Usa el primer ID como columna clave para dropna
                
                if isinstance(df.index, pd.DatetimeIndex):
                    df.index = df.index.to_period('M').to_timestamp()
                else:
                    # En caso de que, por alguna razón, no se pueda establecer el DatetimeIndex
                    print(f"ERROR: No se pudo establecer DatetimeIndex en DatasetAPI. Tipo actual: {type(df.index)}")
                    self.datos = pd.DataFrame() # Asegura un DataFrame vacío para evitar errores posteriores
                    return # Salir de la función si el índice es incorrecto
                # --- FIN DE LAS MODIFICACIONES NECESARIAS ---


                # Convertir las columnas de valores a numérico, manejando posibles errores
                for col in df.columns:
                    if col != 'fecha': # Ahora 'fecha' es el índice, no una columna, pero esta verificación está bien.
                        df[col] = pd.to_numeric(df[col], errors='coerce') 
                
                # Opcional: Eliminar filas donde el valor IPC principal sea NaN después de la conversión numérica
                df = df.dropna(subset=[series_ids[0]]) # Asegura que al menos la serie principal no tenga NaNs


                self.datos = df
                print("Datos del INDEC cargados y procesados exitosamente.")
                print("Primeras 5 filas de los datos cargados (con índice de fecha):")
                print(self.datos.head())
                print(f"Tipo de índice final en DatasetAPI: {type(self.datos.index)}")


                # Llamar a los métodos de validación y transformación de la clase base
                if self.validar_datos():
                    self.transformar_datos()
                    print(f"Tipo de índice después de validar/transformar en DatasetAPI: {type(self.datos.index)}") # Verificación adicional
                else:
                    print("La validación de los datos falló.")

            else:
                print("Estructura de respuesta inesperada de la API o no se encontraron datos válidos.")
                self.datos = pd.DataFrame() # Asegura que self.datos sea un DataFrame vacío
                if 'errors' in data: # Algunas APIs incluyen un campo 'errors'
                    print(f"Errores reportados por la API: {data['errors']}")


        except requests.exceptions.RequestException as e:
            print(f"Error de conexión o HTTP al obtener datos de la API: {e}")
            self.datos = pd.DataFrame()
        except ValueError as e:
            print(f"Error al parsear el JSON o al procesar los datos: {e}")
            self.datos = pd.DataFrame()
        except Exception as e:
            print(f"Ocurrió un error inesperado durante la carga de datos: {e}")
            self.datos = pd.DataFrame()
