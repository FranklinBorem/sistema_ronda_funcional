import cv2

url = "rtsp://teste:Ronda2026%40@10.38.7.202:554/Streaming/channels/101"
cap = cv2.VideoCapture(url)

if cap.isOpened():
    print("✅ Conectou!")
    ret, frame = cap.read()
    print(f"Frame capturado: {ret} | Tamanho: {frame.shape if ret else 'N/A'}")
else:
    print("❌ Falhou")

cap.release()