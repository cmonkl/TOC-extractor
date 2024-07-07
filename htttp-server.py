from flask import Flask, request, jsonify, send_file, Response
import os
import time
from toc_parsing import extract_toc
import io

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/process", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"})

    if file:
        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        processed_filename = f"{os.path.splitext(filename)[0]}_processed.pdf"
        processed_file_path = os.path.join(UPLOAD_FOLDER, processed_filename)
        if os.path.exists(processed_file_path):
            os.remove(processed_file_path)

        response = extract_toc(file_path)

        if response['status'] == 'success':
            #time.sleep(20)  # Waiting for emulate processing time
            file_bytes = io.BytesIO(response['doc'])
            return send_file(file_bytes, mimetype='image/pdf', 
                             download_name=processed_filename, 
                             as_attachment=True)
        else:
            #jsonify({"error": response['status']})
            return Response(response['status'],
                            status=400)
    


if __name__ == "__main__":
    app.run(debug=True)
