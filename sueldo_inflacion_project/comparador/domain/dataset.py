from abc import ABC, abstractmethod


class Dataset(ABC):
    """
    Clase base abstracta para el manejo de conjuntos de datos.
    Define una interfaz común para cargar, validar y transformar datos.
    """
    def __init__(self, fuente=None):
        """
        Inicializa la clase Dataset.

        Args:
            fuente (str, optional): La fuente de los datos (ej. URL de API, ruta de archivo).
                                    Por defecto es None.
        """
        self.__fuente = fuente # Se usa un atributo privado para la propiedad fuente
        self.__datos = None    # Se usa un atributo privado para la propiedad datos

    @property
    def datos(self):
        """
        Propiedad que devuelve el DataFrame de Pandas que contiene los datos.
        """
        return self.__datos

    @datos.setter
    def datos(self, value):
        """
        Setter para la propiedad 'datos'. Establece el DataFrame de Pandas.
        Aquí se pueden añadir validaciones o pre-procesamientos antes de asignar los datos.
        """
        # Aquí puedes añadir validaciones o lógica de pre-procesamiento si es necesario
        self.__datos = value

    @property
    def fuente(self):
        """
        Propiedad que devuelve la fuente de los datos.
        """
        return self.__fuente

    @fuente.setter
    def fuente(self, value):
        """
        Setter para la propiedad 'fuente'. Permite modificar la fuente de los datos.
        """
        self.__fuente = value

   
    def cargar_datos(self, *args, **kwargs):
        """
        Método abstracto para cargar datos. Debe ser implementado por las subclases.
        """
        raise NotImplementedError("El método cargar_datos debe ser implementado por las subclases.")

    def validar_datos(self):
        """
        Valida la integridad de los datos cargados.
        Detecta datos faltantes y filas duplicadas.

        Returns:
            bool: True si la validación es exitosa.

        Raises:
            ValueError: Si los datos no han sido cargados.
        """
        if self.datos is None:
            raise ValueError("Datos no cargados. Ejecute 'cargar_datos' primero.")

        # Contar datos faltantes y duplicados
        missing_data_count = self.datos.isnull().sum().sum()
        duplicate_rows_count = self.datos.duplicated().sum()

        if missing_data_count > 0:
            print(f"Advertencia: {missing_data_count} datos faltantes detectados.")
        if duplicate_rows_count > 0:
            print(f"Advertencia: {duplicate_rows_count} filas duplicadas detectadas.")

        return True

    def transformar_datos(self):
        """
        Aplica transformaciones estándar a los datos, como:
        - Nombres de columnas a minúsculas y snake_case (evitando modificar IDs de series que ya usan '_').
        - Eliminación de filas duplicadas.
        - Eliminación de espacios en blanco en columnas de tipo 'object'.
        """
        if self.datos is not None and not self.datos.empty:
            temp_df = self.datos.copy()

            # Transformar nombres de columnas a snake_case, pero solo si no parecen IDs de series
            # Para IDs de series, el nombre de columna ya debería ser el ID tal cual.
            new_columns = []
            for col in temp_df.columns:
                # Si la columna es 'fecha' o parece un ID de serie (contiene '_'), mantenerlo
                if col == 'fecha' or '_' in col:
                    new_columns.append(col)
                else:
                    new_columns.append(col.lower().replace(" ", "_"))
            temp_df.columns = new_columns

            # Eliminar filas duplicadas
            initial_rows = len(temp_df)
            temp_df = temp_df.drop_duplicates()
            if len(temp_df) < initial_rows:
                print(f"Transformación: Se eliminaron {initial_rows - len(temp_df)} filas duplicadas.")

            # Eliminar espacios en blanco de columnas de tipo 'object'
            for col in temp_df.select_dtypes(include="object").columns:
                temp_df[col] = temp_df[col].astype(str).str.strip()
            
            self.datos = temp_df # Asignar el DataFrame transformado de nuevo
            print("Transformación: Transformaciones básicas aplicadas.")
        else:
            print("Transformación: No hay datos o el DataFrame está vacío para transformar.")

    def mostrar_resumen(self):
        """
        Muestra un resumen estadístico de los datos cargados.
        """
        if self.datos is not None and not self.datos.empty:
            print("\nResumen estadístico de los datos:")
            print(self.datos.describe(include='all'))
        else:
            print("No hay datos para mostrar el resumen.")
