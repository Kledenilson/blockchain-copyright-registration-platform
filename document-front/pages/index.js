import { useState, useEffect } from "react";
import io from "socket.io-client";
import axios from "axios";
import { generateFileHash } from "../utils/hashGenerator";

const socket = io("http://localhost:5000");

export default function Home() {
  const [file, setFile] = useState(null);
  const [hash, setHash] = useState("");
  const [uploadResponse, setUploadResponse] = useState(null);
  const [transactionStatus, setTransactionStatus] = useState(null);

  useEffect(() => {
    socket.on("payment_confirmed", (data) => {
      setTransactionStatus({ status: "confirmed", txid: data.txid });
    });
    return () => {
      socket.off("payment_confirmed");
    };
  }, []);

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
    } catch (error) {
      console.error("Erro no upload:", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center p-5">
      <h1 className="text-2xl font-bold mb-5">Upload de Documento</h1>
      <input type="file" onChange={handleFileChange} className="border p-2" />
      {hash && <p className="mt-2 text-sm">Hash SHA-256: {hash}</p>}
      <button
        onClick={handleUpload}
        className="bg-blue-500 text-white p-2 mt-2 rounded"
      >
        Enviar Arquivo
      </button>

      {uploadResponse && (
        <div className="mt-5 p-3 bg-white shadow rounded">
          <p><b>Endereço para pagamento:</b> {uploadResponse.address}</p>
          <p><b>Arquivo salvo em:</b> {uploadResponse.file_path}</p>
        </div>
      )}

      {transactionStatus && (
        <div className="mt-5 p-3 bg-green-100 shadow rounded">
          <p><b>Status da Transação:</b> {transactionStatus.status}</p>
          <p><b>TXID:</b> {transactionStatus.txid}</p>
        </div>
      )}
    </div>
  );
}
