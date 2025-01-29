import { useState } from "react";
import { generateFileHash } from "../utils/hashGenerator";
import axios from "axios";
import Link from "next/link";

export default function UploadComponent({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [hash, setHash] = useState("");
  const [uploadResponse, setUploadResponse] = useState(null);

  const handleFileChange = async (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    if (selectedFile) {
      const computedHash = await generateFileHash(selectedFile);
      setHash(computedHash);
    }
  };

  const handleUpload = async () => {
    if (!file || !hash) return alert("Selecione um arquivo primeiro!");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("data", hash);

    try {
      const response = await axios.post(
        "http://localhost:5000/api/transaction/upload",
        formData
      );
      setUploadResponse(response.data);
      onUploadSuccess(response.data);
    } catch (error) {
      console.error("Erro no upload:", error);
    }
  };

  return (
    <div className="bg-white shadow-lg p-6 rounded-lg">
      <h2 className="text-xl font-semibold mb-3">Upload de Documento</h2>
      <input type="file" onChange={handleFileChange} className="border p-2 w-full mb-3" />
      {hash && <p className="mt-2 text-sm text-gray-600">Hash SHA-256: {hash}</p>}
      <button onClick={handleUpload} className="bg-blue-500 text-white p-2 w-full rounded hover:bg-blue-600">
        Enviar Arquivo
      </button>

      {uploadResponse && (
        <div className="mt-5 p-3 bg-gray-100 shadow rounded">
          <p><b>Endereço para pagamento:</b> {uploadResponse.address}</p>
          <p><b>Arquivo salvo em:</b> {uploadResponse.file_path}</p>
          <Link href="/history">
            <a className="text-blue-600 underline mt-2 block">Ver Histórico de Transações</a>
          </Link>
        </div>
      )}
    </div>
  );
}
