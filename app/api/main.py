import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import predict

app = FastAPI(title="Prediksi Konsumsi Energi Gedung")


class Masukan(BaseModel):
    tanggal: str
    suhu_C: float
    okupansi_puncak: int
    hari_libur: int = 0


@app.get("/")
def info():
    return {"model": predict._meta["model"], "metrik": predict._meta["metrik"],
            "data_terakhir": str(predict.TERAKHIR.date())}


@app.post("/prediksi")
def prediksi(m: Masukan):
    try:
        df = predict.prediksi_hari(m.tanggal, m.suhu_C, m.okupansi_puncak, m.hari_libur)
    except predict.InputTidakValid as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"tanggal": m.tanggal, "total_kWh": round(float(df.prediksi_kWh.sum()), 1),
            "per_jam": df.to_dict("records")}
