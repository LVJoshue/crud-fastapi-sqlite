import sqlite3
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="CRUD Usuarios, Materias y Paralelos - SQLite")

DB_NAME = "database.db"


def get_db():
    """Crea la conexión local con SQLite y activa las claves foráneas."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  
    conn.execute("PRAGMA foreign_keys = ON")  
    return conn


def init_db():
    """Crea las 3 tablas (paralelos, usuarios y materias) si no existen."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS paralelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_paralelo TEXT NOT NULL,
            aula TEXT NOT NULL,
            jornada TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_estudiante TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            correo TEXT NOT NULL,
            semestre INTEGER NOT NULL,
            paralelo_id INTEGER NOT NULL,
            FOREIGN KEY (paralelo_id) REFERENCES paralelos (id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS materias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_materia TEXT NOT NULL,
            creditos INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


init_db()


class ParaleloCrear(BaseModel):
    nombre_paralelo: str
    aula: str
    jornada: str

class ParaleloActualizar(BaseModel):
    nombre_paralelo: Optional[str] = None
    aula: Optional[str] = None
    jornada: Optional[str] = None


class UsuarioCrear(BaseModel):
    codigo_estudiante: str
    nombre: str
    apellido: str
    correo: str
    semestre: int
    paralelo_id: int  

class UsuarioActualizar(BaseModel):
    codigo_estudiante: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    correo: Optional[str] = None
    semestre: Optional[int] = None
    paralelo_id: Optional[int] = None


class MateriaCrear(BaseModel):
    nombre_materia: str
    creditos: int
    usuario_id: int  

class MateriaActualizar(BaseModel):
    nombre_materia: Optional[str] = None
    creditos: Optional[int] = None
    usuario_id: Optional[int] = None


@app.post("/paralelos/", status_code=201, tags=["1. Paralelos"])
def crear_paralelo(paralelo: ParaleloCrear):
    """Crea un nuevo paralelo en la base de datos."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO paralelos (nombre_paralelo, aula, jornada) VALUES (?, ?, ?)",
        (paralelo.nombre_paralelo, paralelo.aula, paralelo.jornada),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **paralelo.model_dump()}


@app.get("/paralelos/", tags=["1. Paralelos"])
def obtener_paralelos():
    """Lista todos los paralelos registrados."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM paralelos")
    filas = cursor.fetchall()
    conn.close()
    return [dict(fila) for fila in filas]


@app.put("/paralelos/{paralelo_id}", tags=["1. Paralelos"])
def actualizar_paralelo(paralelo_id: int, datos: ParaleloActualizar):
    """Actualiza un paralelo existente por su ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM paralelos WHERE id = ?", (paralelo_id,))
    fila = cursor.fetchone()
    if fila is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Paralelo no encontrado")

    actual = dict(fila)
    nombre_paralelo = datos.nombre_paralelo if datos.nombre_paralelo is not None else actual["nombre_paralelo"]
    aula = datos.aula if datos.aula is not None else actual["aula"]
    jornada = datos.jornada if datos.jornada is not None else actual["jornada"]

    cursor.execute(
        "UPDATE paralelos SET nombre_paralelo = ?, aula = ?, jornada = ? WHERE id = ?",
        (nombre_paralelo, aula, jornada, paralelo_id),
    )
    conn.commit()
    conn.close()
    return {"id": paralelo_id, "nombre_paralelo": nombre_paralelo, "aula": aula, "jornada": jornada}


@app.delete("/paralelos/{paralelo_id}", tags=["1. Paralelos"])
def eliminar_paralelo(paralelo_id: int):
    """Elimina un paralelo por su ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM paralelos WHERE id = ?", (paralelo_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Paralelo no encontrado")

    cursor.execute("DELETE FROM paralelos WHERE id = ?", (paralelo_id,))
    conn.commit()
    conn.close()
    return {"mensaje": f"Paralelo con ID {paralelo_id} eliminado exitosamente"}



@app.post("/usuarios/", status_code=201, tags=["2. Usuarios"])
def crear_usuario(usuario: UsuarioCrear):
    """Crea un usuario asignándole un único paralelo."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM paralelos WHERE id = ?", (usuario.paralelo_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="El paralelo_id especificado no existe")

    try:
        cursor.execute(
            """
            INSERT INTO usuarios (codigo_estudiante, nombre, apellido, correo, semestre, paralelo_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                usuario.codigo_estudiante,
                usuario.nombre,
                usuario.apellido,
                usuario.correo,
                usuario.semestre,
                usuario.paralelo_id,
            ),
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="El codigo_estudiante ya existe")

    conn.close()
    return {"id": nuevo_id, **usuario.model_dump()}


@app.get("/usuarios/", tags=["2. Usuarios"])
def obtener_usuarios():
    """Obtiene todos los usuarios registrados."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios")
    filas = cursor.fetchall()
    conn.close()
    return [dict(fila) for fila in filas]


@app.get("/usuarios/{usuario_id}", tags=["2. Usuarios"])
def obtener_usuario_con_relaciones(usuario_id: int):
    """Obtiene un usuario junto con su único paralelo y todas sus materias."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT u.*, p.nombre_paralelo, p.aula, p.jornada
        FROM usuarios u
        JOIN paralelos p ON u.paralelo_id = p.id
        WHERE u.id = ?
        """,
        (usuario_id,),
    )
    usuario = cursor.fetchone()
    if usuario is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cursor.execute("SELECT * FROM materias WHERE usuario_id = ?", (usuario_id,))
    materias = [dict(m) for m in cursor.fetchall()]
    conn.close()

    resultado = dict(usuario)
    resultado["materias_inscritas"] = materias
    return resultado


@app.put("/usuarios/{usuario_id}", tags=["2. Usuarios"])
def actualizar_usuario(usuario_id: int, datos: UsuarioActualizar):
    """Actualiza los datos de un usuario."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
    fila_actual = cursor.fetchone()
    if fila_actual is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    actual = dict(fila_actual)
    codigo_estudiante = datos.codigo_estudiante if datos.codigo_estudiante is not None else actual["codigo_estudiante"]
    nombre = datos.nombre if datos.nombre is not None else actual["nombre"]
    apellido = datos.apellido if datos.apellido is not None else actual["apellido"]
    correo = datos.correo if datos.correo is not None else actual["correo"]
    semestre = datos.semestre if datos.semestre is not None else actual["semestre"]
    paralelo_id = datos.paralelo_id if datos.paralelo_id is not None else actual["paralelo_id"]

    cursor.execute(
        """
        UPDATE usuarios
        SET codigo_estudiante = ?, nombre = ?, apellido = ?, correo = ?, semestre = ?, paralelo_id = ?
        WHERE id = ?
        """,
        (codigo_estudiante, nombre, apellido, correo, semestre, paralelo_id, usuario_id),
    )
    conn.commit()
    conn.close()
    return {
        "id": usuario_id,
        "codigo_estudiante": codigo_estudiante,
        "nombre": nombre,
        "apellido": apellido,
        "correo": correo,
        "semestre": semestre,
        "paralelo_id": paralelo_id,
    }


@app.delete("/usuarios/{usuario_id}", tags=["2. Usuarios"])
def eliminar_usuario(usuario_id: int):
    """Elimina un usuario por su ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cursor.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    conn.close()
    return {"mensaje": f"Usuario con ID {usuario_id} eliminado exitosamente"}



@app.post("/materias/", status_code=201, tags=["3. Materias"])
def crear_materia(materia: MateriaCrear):
    """Registra una materia y la asocia a un usuario existente."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuarios WHERE id = ?", (materia.usuario_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="El usuario_id especificado no existe")

    cursor.execute(
        "INSERT INTO materias (nombre_materia, creditos, usuario_id) VALUES (?, ?, ?)",
        (materia.nombre_materia, materia.creditos, materia.usuario_id),
    )
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **materia.model_dump()}


@app.get("/materias/", tags=["3. Materias"])
def obtener_materias():
    """Lista todas las materias registradas."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materias")
    filas = cursor.fetchall()
    conn.close()
    return [dict(fila) for fila in filas]


@app.put("/materias/{materia_id}", tags=["3. Materias"])
def actualizar_materia(materia_id: int, datos: MateriaActualizar):
    """Actualiza una materia existente."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM materias WHERE id = ?", (materia_id,))
    fila_actual = cursor.fetchone()
    if fila_actual is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    actual = dict(fila_actual)
    nombre_materia = datos.nombre_materia if datos.nombre_materia is not None else actual["nombre_materia"]
    creditos = datos.creditos if datos.creditos is not None else actual["creditos"]
    usuario_id = datos.usuario_id if datos.usuario_id is not None else actual["usuario_id"]

    cursor.execute(
        "UPDATE materias SET nombre_materia = ?, creditos = ?, usuario_id = ? WHERE id = ?",
        (nombre_materia, creditos, usuario_id, materia_id),
    )
    conn.commit()
    conn.close()
    return {"id": materia_id, "nombre_materia": nombre_materia, "creditos": creditos, "usuario_id": usuario_id}


@app.delete("/materias/{materia_id}", tags=["3. Materias"])
def eliminar_materia(materia_id: int):
    """Elimina una materia por su ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM materias WHERE id = ?", (materia_id,))
    if cursor.fetchone() is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    cursor.execute("DELETE FROM materias WHERE id = ?", (materia_id,))
    conn.commit()
    conn.close()
    return {"mensaje": f"Materia con ID {materia_id} eliminada exitosamente"}