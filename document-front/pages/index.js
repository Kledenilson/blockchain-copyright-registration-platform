import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import { generateFileHash } from "../utils/hashGenerator";
import Header from "../components/Header";
import Toaster from "../components/Toaster";
import io from "socket.io-client";
import { BsUpload, BsCheckCircle, BsEye } from "react-icons/bs"; // Importando o ícone de visualização

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const socket = io(API_URL);

export default function Home() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [address, setAddress] = useState("");
  const [searchAddress, setSearchAddress] = useState("");
  const [amount, setAmount] = useState(0.0001); // Definindo o valor inicial de amount como 0.0001
  const [hash, setHash] = useState("");
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState("success");
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [showDownloadModal, setShowDownloadModal] = useState(false);
  const [txHash, setTxHash] = useState("");
  const [fileDownloadLink, setFileDownloadLink] = useState("");
  const router = useRouter();

  useEffect(() => {
    socket.on("payment_confirmed", (data) => {
      if (data.address === address) {
        showToast("Your payment has been successfully received!", "success");
        setTxHash(data.txid);
        setFileDownloadLink(`${API_URL}/api/files/${data.txid}`);
        setShowDownloadModal(true);
      }
    });
    return () => {
      socket.off("payment_confirmed");
    };
  }, [address]);

  useEffect(() => {
    if (file && hash) {
      handleUpload();
    }
  }, [file, hash]);

  const showToast = (message, type = "success") => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleFileChange = async (event) => {
    const selectedFile = event.target.files[0];
    setFile(selectedFile);
    if (selectedFile) {
      try {
        const computedHash = await generateFileHash(selectedFile);
        setHash(computedHash);
      } catch (error) {
        console.error("Error generating hash:", error);
        showToast("Failed to generate hash. Try again.", "error");
      }
    }
  };

  const handleUpload = async () => {
    if (!file || !hash) {
      showToast("Select a file before uploading!", "error");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("data", hash);
    try {
      const response = await axios.post(
        `${API_URL}/api/transaction/upload`,
        formData
      );
      setUploadResponse(response.data);
      setAddress(response.data.address);
      showToast("File uploaded successfully!", "success");
      setShowPaymentModal(true);
    } catch (error) {
      console.error("Upload error:", error);
      showToast("Failed to upload file. Try again.", "error");
    }
  };

  const handlePayment = async () => {
    if (!address) {
      showToast("No payment address available!", "error");
      return;
    }
    try {
      const response = await axios.post(
        `${API_URL}/api/transaction/send`,
        {
          address: address,
          amount: amount,
        }
      );
      showToast("Payment sent! Await confirmation... Track you registration.", "success");
      setShowPaymentModal(false);
    } catch (error) {
      console.error("Payment error:", error);
      showToast("Payment failed. Try again.", "error");
    }
  };

  const handleSearch = () => {
    if (!searchAddress) {
      showToast("Enter an address to search!", "error");
      return;
    }
    router.push(`/history?address=${searchAddress}`);
  };

  const handleTrackStatus = () => {
    if (!searchAddress) {
      showToast("Enter an address to search!", "error");
      return;
    }
    // Chama o mesmo endpoint do handleSearch
    router.push(`/history?address=${searchAddress}`);
  };

  return (
    <div className="container mt-12">
      <Header />
      <Toaster message={toastMessage} type={toastType} />
      <div className="container my-5">
        <div className="row justify-content-center">
          <div className="col-md-8" style={{ marginTop: "-40px" }}>
            <blockquote className="blockquote border-start border-4 border-primary p-4 shadow-sm">
              <p className="mb-3" style={{ fontSize: "0.9em" }}>
                Register your documents, works and all files that require
                integrity and preserved authorship here now on the blockchain.
                Get secure, high-tech proof in a decentralized way.
              </p>
              <footer className="blockquote-footer" style={{ fontSize: "0.7em" }}>
                You only need to donate a minimum of{" "}
                <cite title="BTC Donation">0.0001 BTC</cite>.
              </footer>
            </blockquote>
          </div>
        </div>
      </div>
      {/* Card de Upload */}
      <div className="row justify-content-center" style={{marginTop: "-50px", marginBottom: "-50px"}}>
        <div className="col-md-6 text-center">
          <div className="card bg-transparent border-0 shadow-none p-4 mb-4">
            <h4 className="card-title" style={{fontFamily: 'Orbitron'}}>Upload your file now</h4>
            <div className="card-body">
              <input
                type="file"
                className="d-none"
                id="fileInput"
                onChange={handleFileChange}
              />
              <button
                className="btn btn-primary w-100 mb-3" style={{backgroundColor: 'transparent', border: 'none', color: 'gray', fontSize: '1.5em'}}
                onClick={() => document.getElementById("fileInput").click()}
              > Click here
                <BsUpload style={{color: 'gray', marginLeft: '15px'}} />
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* Cards de Acompanhamento e Verificação */}
      <div className="row justify-content-center">
        <div className="col-md-10 d-flex">
          {/* Card de Acompanhamento do Status */}
          <div className="card shadow p-4 mb-2 flex-fill me-3">
            <h4 className="card-title" style={{fontFamily: 'Orbitron'}}>Track Your Registration Status</h4>
            <div className="card-body">
              <input
                type="text"
                className="form-control mb-3"
                placeholder="Paste the wallet address here"
                value={searchAddress}
                onChange={(e) => setSearchAddress(e.target.value)}
              />
              <button className="btn btn-secondary w-100" onClick={handleTrackStatus} style={{fontSize: '1.5em'}}>
                <BsEye />
              </button>
            </div>
          </div>
          {/* Card de Verificação */}
          <div className="card shadow p-4 mb-2 flex-fill">
            <h4 className="card-title" style={{fontFamily: 'Orbitron'}}>Validate authenticity records here</h4>
            <div className="card-body">
              <input
                type="text"
                className="form-control mb-3"
                placeholder="Paste the registration hash here"
                value={searchAddress}
                onChange={(e) => setSearchAddress(e.target.value)}
              />
              <button className="btn btn-secondary w-100" onClick={handleSearch} style={{fontSize: '1.5em'}}>
                <BsCheckCircle />
              </button>
            </div>
          </div>
        </div>
      </div>
      {showPaymentModal && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title" style={{fontFamily: 'Orbitron', fontSize: '1.5em', fontWeight: '600'}}>Make a Payment</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowPaymentModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <div className="form-group">
                  <label htmlFor="paymentAddress"  style={{fontWeight: '600'}}>Payment to Wallet Address</label>
                  <input
                    type="text"
                    className="form-control mb-3"
                    id="paymentAddress"
                    value={address}
                    readOnly
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="paymentAmount" style={{fontWeight: '600'}}>Amount (BTC)</label>
                  <input
                    type="number"
                    className="form-control mb-3"
                    id="paymentAmount"
                    value={amount}
                    onChange={(e) => setAmount(parseFloat(e.target.value))}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={() => setShowPaymentModal(false)}>
                  Close
                </button>
                <button className="btn btn-success" onClick={handlePayment}>
                  Pay Now
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {showDownloadModal && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Payment Confirmed</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowDownloadModal(false)}
                ></button>
              </div>
              <div className="modal-body">
                <p>Your payment has been received. Download your document below.</p>
                <a href={fileDownloadLink} className="btn btn-primary w-100" target="_blank">
                  Download File
                </a>
                <input type="text" className="form-control mt-3" value={txHash} readOnly />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}