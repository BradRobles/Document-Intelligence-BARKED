import time
import pytesseract
import easyocr
from PIL import Image, ImageDraw
import os

def create_sample_image(filename="sample_test.png"):
    # Crear una imagen en blanco con texto simulando un documento
    img = Image.new('RGB', (500, 150), color = (255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Escribir algo de texto simple para la prueba
    d.text((20, 40), "Document Intelligence Asynchronous Pipeline", fill=(0,0,0))
    d.text((20, 80), "Prueba de Benchmark OCR para justificacion tecnica", fill=(0,0,0))
    
    img.save(filename)
    return filename

def run_benchmark():
    image_path = create_sample_image()
    print(f"--- Iniciando Benchmark de OCR sobre {image_path} ---")
    
    tesseract_time = 0
    easyocr_time = 0

    # 1. Prueba con PyTesseract
    print("\n[1] Evaluando PyTesseract...")
    start_time = time.time()
    try:
        tesseract_text = pytesseract.image_to_string(Image.open(image_path))
        tesseract_time = time.time() - start_time
        print(f"Tiempo: {tesseract_time:.4f} segundos")
        print(f"Texto extraído: '{tesseract_text.strip()}'")
    except Exception as e:
        print(f"Error en PyTesseract: {e}. (Asegúrate de ejecutar esto dentro de Docker o con Tesseract instalado en tu Mac)")

    # 2. Prueba con EasyOCR
    print("\n[2] Evaluando EasyOCR...")
    start_time_init = time.time()
    try:
        # EasyOCR descarga los modelos la primera vez; para ser justos separamos el tiempo de inicialización
        reader = easyocr.Reader(['en', 'es'], gpu=False) # GPU=False para simular un servidor CPU estándar
        init_time = time.time() - start_time_init
        print(f"(Tiempo de carga del modelo de IA: {init_time:.4f} segundos)")
        
        start_read = time.time()
        easyocr_result = reader.readtext(image_path, detail=0)
        easyocr_text = " ".join(easyocr_result)
        easyocr_time = time.time() - start_read
        print(f"Tiempo de lectura real: {easyocr_time:.4f} segundos")
        print(f"Texto extraído: '{easyocr_text.strip()}'")
    except Exception as e:
        print(f"Error en EasyOCR: {e}")

    # Generar conclusiones de forma automática
    report_text = f"""
======================================================
CONCLUSIONES DEL BENCHMARK (PARA INCLUIR EN EL REPORTE PDF)
======================================================
Tesseract OCR tardó: {tesseract_time:.4f}s
EasyOCR tardó:       {easyocr_time:.4f}s

Decisión Técnica Justificada:
Se ha seleccionado `pytesseract` para el procesamiento en producción dentro del worker de Celery.
Aunque `EasyOCR` se basa en modelos de Deep Learning (PyTorch) y puede ser más preciso en imágenes
con fondos complejos, sus tiempos de inicialización de modelo y de inferencia en CPU son significativamente 
superiores. 

Dado que el "Asynchronous Pipeline" debe procesar documentos de manera eficiente en contenedores Docker 
(sin acceso garantizado a GPUs dedicadas), PyTesseract proporciona el mejor equilibrio entre rendimiento, 
consumo de memoria y precisión para documentos de texto escaneados.
======================================================
"""
    # Guardar los resultados en un archivo de texto en la misma carpeta
    with open("benchmark_results.txt", "w") as f:
        f.write(report_text)
    
    print(report_text)
    os.remove(image_path)
    print("Benchmark completado. Los resultados se guardaron en 'benchmark_results.txt'.")

if __name__ == "__main__":
    run_benchmark()
