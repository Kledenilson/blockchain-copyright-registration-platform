import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import io from "socket.io-client";
import axios from "axios";

const socket = io("http://localhost:5000");

export default function Home() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [address, setAddress] = useState("");
  const router = useRouter();

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file to upload!");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("data", "123456abcdef"); // Mock hash for testing

    try {
      const response = await axios.post(
        "http://localhost:5000/api/transaction/upload",
        formData
      );
      setUploadResponse(response.data);
      setAddress(response.data.address);
    } catch (error) {
      console.error("Upload error:", error);
    }
  };

  const handlePayment = () => {
    if (!address) return alert("No payment address available!");
    if (confirm(`Confirm payment to address: ${address}`)) {
      router.push("/history"); // Redirect to history page
    }
  };

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4 text-primary">Blockchain Copyright Platform</h1>

      {/* Upload Section */}
      <div className="card shadow p-4 mb-5">
        <h3 className="card-title">Upload Your File</h3>
        <div className="card-body">
          <input
            type="file"
            className="form-control mb-3"
            onChange={handleFileChange}
          />
          <button
            className="btn btn-primary w-100"
            onClick={handleUpload}
          >
            Upload File
          </button>
        </div>
      </div>

      {/* Payment Section */}
      {uploadResponse && (
        <div className="card shadow p-4 mb-5">
          <h3 className="card-title">Make a Payment</h3>
          <div className="card-body">
            <div className="form-group">
              <label htmlFor="paymentAddress">Payment Address</label>
              <input
                type="text"
                className="form-control mb-3"
                id="paymentAddress"
                value={address}
                readOnly
              />
            </div>
            <button
              className="btn btn-success w-100"
              onClick={handlePayment}
            >
              Pay Now
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
