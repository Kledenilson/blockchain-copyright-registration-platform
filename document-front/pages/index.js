import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import { generateFileHash } from "../utils/hashGenerator";
import Header from "../components/Header";
import Toaster from "../components/Toaster";
import io from "socket.io-client";

const socket = io("http://localhost:5000");

export default function Home() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [address, setAddress] = useState("");
  const [searchAddress, setSearchAddress] = useState("");
  const [amount, setAmount] = useState(0.01);
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
        setFileDownloadLink(`http://localhost:5000/api/files/${data.txid}`);
        setShowDownloadModal(true);
      }
    });

    return () => {
      socket.off("payment_confirmed");
    };
  }, [address]);

  const showToast = (message, type = "success") => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => setToastMessage(null), 3000);
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
        "http://localhost:5000/api/transaction/upload",
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
        "http://localhost:5000/api/transaction/send",
        {
          address: address,
          amount: amount,
        }
      );
      showToast("Payment sent! Await confirmation...", "success");
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

  return (
    <div className="container mt-5">
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
                <cite title="BTC Donation">0.01 BTC</cite>.
              </footer>
            </blockquote>
          </div>
        </div>
      </div>
      <div className="card shadow p-4 mb-5">
        <h4 className="card-title">Upload your file now</h4>
        <div className="card-body">
          <input
            type="file"
            className="form-control mb-3"
            onChange={handleFileChange}
          />
          <button className="btn btn-primary w-100 mb-3" onClick={handleUpload}>
            Upload file
          </button>
        </div>
      </div>

      <div className="card shadow p-4 mb-5">
        <h4 className="card-title">Validate record hashes here</h4>
        <div className="card-body">
          <input
            type="text"
            className="form-control mb-3"
            placeholder="Paste the registration hash here"
            value={searchAddress}
            onChange={(e) => setSearchAddress(e.target.value)}
          />
          <button className="btn btn-secondary w-100" onClick={handleSearch}>
            Check authenticity
          </button>
        </div>
      </div>

      {showPaymentModal && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Make a Payment</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowPaymentModal(false)}
                ></button>
              </div>
              <div className="modal-body">
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
                <div className="form-group">
                  <label htmlFor="paymentAmount">Amount (BTC)</label>
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
