import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import { generateFileHash } from "../utils/hashGenerator";
import Header from "../components/Header";
import Toaster from "../components/Toaster";
import io from "socket.io-client";
import { BsUpload, BsCheckCircle, BsEye, BsSearch, BsArrowClockwise } from "react-icons/bs";

const API_URL = process.env.NEXT_PUBLIC_API_URL;
const socket = io(API_URL);

export default function Home() {
  const [file, setFile] = useState(null);
  const [uploadResponse, setUploadResponse] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
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
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [historyTransactions, setHistoryTransactions] = useState([]);
  const [historySelectedTransaction, setHistorySelectedTransaction] = useState(null);
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

    setIsLoading(true);

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
    } finally {
      setIsLoading(false); 
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
      showToast("Payment sent! Await confirmation...", "success");
      setShowPaymentModal(false);
      // Carregar os detalhes da transação na modal de histórico
      fetchHistoryTransactions(address);
      setShowHistoryModal(true);
    } catch (error) {
      console.error("Payment error:", error);
      showToast("Payment failed. Try again.", "error");
    }
  };

  const handleSearch = () => {
    if (!searchAddress) {
      showToast("Enter an registration hash to search!", "error");
      return;
    }
    router.push(`/history?address=${searchAddress}`);
  };

  const handleTrackStatus = () => {
    if (!searchAddress) {
      showToast("Enter an address to search!", "error");
      return;
    }

    //fetchHistoryTransactions(searchAddress);
    //setShowHistoryModal(true);
    // Chama o mesmo endpoint do handleSearch
    router.push(`/history?address=${searchAddress}`);
  };

  const handleCloseModals = () => {
    setShowPaymentModal(false);
    setShowDownloadModal(false);
    setShowHistoryModal(false);
    setHistoryTransactions([]);
    setHistorySelectedTransaction(null);
  };

  const fetchHistoryTransactions = async (address) => {
    if (!address) return; // Aguarda o endereço estar disponível
    try {
      const response = await axios.get(
        `${API_URL}/api/transactions/${address}`
      );      
      setHistoryTransactions(response.data.transactions);
    } catch (error) {
      console.error("Error fetching transactions:", error);
      showToast("Failed to fetch transactions. Try again.", "error");
    }
  };

  const fetchTransactionDetails = async (txid) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/transaction/${txid}`
      );      
      setHistorySelectedTransaction(response.data);
    } catch (error) {
      console.error("Error fetching transaction details:", error);
      showToast("Failed to fetch transaction details. Try again.", "error");
    }
  };

  return (
    <div className="container mt-12">
      <Header />
      <Toaster message={toastMessage} type={toastType} />
      <div className="container my-5">
        <div className="row justify-content-center">
          <div className="col-md-8" style={{ marginTop: "-40px" }}>
            <blockquote className="blockquote border-start border-0 p-4">
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
      <div className="row justify-content-center" style={{marginTop: "-70px", marginBottom: "-50px"}}>
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
                className="btn btn-primary w-100 mb-3" style={{border: 'none', color: 'white', fontSize: '1.4em'}}
                onClick={() => document.getElementById("fileInput").click()}
              > Click here
                <BsUpload style={{color: 'white', marginLeft: '15px'}} />
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
              <button className="btn btn-primary w-100" onClick={handleTrackStatus} style={{fontSize: '1.5em'}}>
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
                //value={searchAddress}
                //onChange={(e) => setSearchAddress(e.target.value)}
              />
              <button className="btn btn-primary w-100" style={{fontSize: '1.5em'}}>
                <BsCheckCircle />
              </button>
            </div>
          </div>
        </div>
      </div>
      {showPaymentModal && (
        <div className="modal-overlay">
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
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
        </div>
      )}
      {showHistoryModal && (
      <>
        <div className="modal-overlay" onClick={handleCloseModals}></div>
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title" style={{fontFamily: 'Orbitron', fontSize: '1.5em', fontWeight: '600'}}>Transaction Details</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={handleCloseModals}
                ></button>
              </div>
              <div className="modal-body">
                {/* <h1 className="text-center mb-4 text-primary">Transaction Details</h1> */}
                <div className="card shadow p-4">
                  <h6 className="card-title" style={{fontSize: '1.2em', textAlign: 'center'}}>
                  Save now in a safe place, the codes below to check the transaction: <p><b>{address}</b></p></h6>
                  <div className="card-body">
                    {historyTransactions.length === 0 ? (
                      <p className="text-center text-muted">No transactions found for this address.</p>
                    ) : (
                      <table className="table table-striped">
                        <thead>
                          <tr>
                            <th>TXID</th>                            
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {historyTransactions.map((tx) => (
                            <tr key={tx.txids}>
                              <td>
                                <button
                                  className="btn btn-link p-0 d-flex align-items-center"                                  
                                  onClick={() => fetchTransactionDetails(tx.txids)}
                                >  <BsSearch className="me-2" style={{fontSize: '0.9em'}}/>                                
                                <div style={{fontWeight: '200', TextDecoration: 'none', fontSize: '1em'}}>
                                   {tx.txids}
                                </div>                                 
                                </button>
                              </td>                             
                              <td>
                                <span
                                  className={`badge ${
                                    tx.status === "success"
                                      ? "bg-success"
                                      : "bg-warning text-dark"
                                  }`}
                                >
                                  {tx.status ? "success" : "pending"}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>
                {/* Detalhes da transação selecionada */}
                {historySelectedTransaction && (
                  <div className="card shadow p-4 mt-4">
                    <h3 className="card-title" style={{fontFamily: 'Orbitron', fontSize: '1.5em', fontWeight: '600'}}>
                    Registration transaction details</h3>
                    <div className="card-body">
                      <p><strong>TXID:</strong> {historySelectedTransaction.transaction.txid}</p>
                      <p><strong>Received By:</strong> {historySelectedTransaction.transaction.vout[1].scriptPubKey.address}</p>
                      <p><strong>Amount:</strong> {historySelectedTransaction.transaction.vout[1].value} BTC</p>
                      <p><strong>Status:</strong> 
                        <span className={`badge ${historySelectedTransaction.status === "success" ? "bg-success" : "bg-warning text-dark"}`}>
                          {historySelectedTransaction.status || "pending"}
                        </span>
                      </p>
                      
                      <p><strong>Date:</strong> {historySelectedTransaction.time
                        ? new Date(historySelectedTransaction.time * 1000).toLocaleString("pt-BR", {
                            day: "2-digit",
                            month: "2-digit",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "No Date Available"}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </>
    )}
      {showDownloadModal && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
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
      {isLoading && (
        <div className="loading-overlay-white">
          <div className="loading-spinner">
            <BsArrowClockwise className="spinner-icon" />
          </div>
        </div>
      )}
      <style jsx global>{`       
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(0, 0, 0, 0.5);
          z-index: 1040;
        }
        .loading-overlay-white {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(255, 255, 255, 0.8); /* Overlay branco transparente */
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1050; /* Garante que o overlay fique acima de tudo */
        }

        .loading-spinner {
          font-size: 3rem;
          color: #007bff; /* Cor do spinner */
          animation: spin 1s linear infinite; /* Animação de rotação */
        }

        @keyframes spin {
          0% {
            transform: rotate(0deg);
          }
          100% {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}