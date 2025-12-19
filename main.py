from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from contextlib import contextmanager

app = FastAPI(title="Product Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'products'),
    'user': os.getenv('DB_USER', 'productuser'),
    'password': os.getenv('DB_PASSWORD', 'productpass')
}

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

class Mahasiswa(BaseModel):
    nim: str
    nama: str
    jurusan: str
    angkatan: int = Field(ge=0)

# Database connection pool
@contextmanager
def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

@app.on_event("startup")
async def startup_event():
    try:
        with get_db_connection() as conn:
            print("Acad Service: Connected to PostgreSQL")
    except Exception as e:
        print(f"Acad Service: PostgreSQL connection error: {e}")

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "Acad Service is running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/acad/mahasiswa")
async def get_mahasiswas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM mahasiswa"

            cursor.execute(query)
            rows = cursor.fetchall()

            return [{"nim": row[0], "nama": row[1], "jurusan": row[2], "angkatan": row[3]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# TASK OPSIONAL 5: Melengkapi code main.py di file \acad-service\main.py
@app.get("/api/acad/ips")
async def get_ips(nim: str = Query(default="22002", description="NIM Mahasiswa")):  # PENAMBAHAN: tambahkan code anda disini
     try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
                        
            query = "select m.nim, m.nama, m.jurusan, krs.nilai, mk.sks  from mahasiswa m join krs on krs.nim = m.nim join mata_kuliah mk ON mk.kode_mk = krs.kode_mk where m.nim = %s"

            cursor.execute(query, (nim,))
            rows = cursor.fetchall()
            
            if not rows:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Mahasiswa dengan NIM {nim} tidak ditemukan atau belum memiliki data KRS"
                )
            
            bobot_nilai = {
                'A': 4.0,     
                'A-': 3.75,    
                'B+': 3.5,     
                'B': 3.0,      
                'B-': 2.75,    
                'C+': 2.5,    
                'C': 2.0,     
                'D': 1.0,      
                'E': 0.0      
            }
            
            total_bobot_x_sks = 0.0  
            total_sks = 0            
            
            nim_mhs = rows[0][0]      
            nama_mhs = rows[0][1]     
            jurusan_mhs = rows[0][2]  
            
            detail_mk = []
            
            # PROSES PERHITUNGAN IPS
            for row in rows:
                nilai = row[3].strip().upper() 
                sks = row[4]    
                
                bobot = bobot_nilai.get(nilai, 0.0)
                
                bobot_x_sks = bobot * sks
                
                total_bobot_x_sks += bobot_x_sks
                total_sks += sks
                
                detail_mk.append({
                    "nilai": nilai,
                    "sks": sks,
                    "bobot": bobot,
                    "kontribusi": round(bobot_x_sks, 2)
                })
            
            # Formula IPS: (Σ(bobot × sks)) / (Σ sks)
            if total_sks > 0:
                ips = total_bobot_x_sks / total_sks
            else:
                ips = 0.0
            
            return {
                "nim": nim_mhs,
                "nama": nama_mhs,
                "jurusan": jurusan_mhs,
                "detail_mata_kuliah": detail_mk,  
                "total_sks": total_sks,
                "total_bobot_x_sks": round(total_bobot_x_sks, 2),
                "ips": round(ips, 2)  
            }

     except HTTPException:
        # Re-raise HTTPException agar status code tetap sesuai (404, dll)
        raise
     except Exception as e:
        # Tangkap error lain dan kembalikan sebagai 500 Internal Server Error
        raise HTTPException(status_code=500, detail=str(e))