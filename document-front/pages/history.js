import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import io from "socket.io-client";
import { BsSearch } from "react-icons/bs"; // Importando o ícone de busca
import Header from "../components/Header";
import Toaster from "../components/Toaster";

// Inicializa o WebSocket
const API_URL = process.env.NEXT_PUBLIC_API_URL;
const socket = io(API_URL);

export default function History() {
  const [transactions, setTransactions] = useState([]);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [toastType, setToastType] = useState("success");

  const router = useRouter();
  const { address } = router.query; // Obtém o endereço da query string

  // Busca as transações da API
  const fetchTransactions = async () => {
    if (!address) return; // Aguarda o endereço estar disponível
    try {
      const response = await axios.get(
        `${API_URL}/api/transactions/${address}`
      );
      
      // Garante que as transações tenham o formato correto
      const formattedTransactions = response.data.transactions.map(tx => ({
        ...tx,
        amount: tx.amount || 0, // Garante que o amount seja um número
        status: tx.status || "pending", // Garante que o status seja definido
      }));
console.log("dados aqui: ", formattedTransactions);
      setTransactions(formattedTransactions);
    } catch (error) {
      console.error("Error fetching transactions:", error);
      showToast("Failed to fetch transactions. Try again.", "error");
    }
  };

  // Atualiza as transações em tempo real via WebSocket
  useEffect(() => {
    fetchTransactions();
    socket.on("payment_confirmed", (data) => {
      console.log("New transaction confirmed:", data);
      // Adiciona ou atualiza a transação na lista existente
      setTransactions((prev) => {
        const existingTx = prev.find((tx) => tx.txid === data.txid);
        if (existingTx) {
          return prev.map((tx) =>
            tx.txid === data.txid ? { ...tx, ...data } : tx
          );
        } else {
          return [...prev, data];
        }
      });
    });
    return () => {
      socket.off("payment_confirmed");
    };
  }, [address]);

  // Busca detalhes de uma transação específica
  const fetchTransactionDetails = async (txid) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/transaction/${txid}`
      );
      setSelectedTransaction(response.data.transaction);
    } catch (error) {
      console.error("Error fetching transaction details:", error);
      showToast("Failed to fetch transaction details. Try again.", "error");
    }
  };

  const showToast = (message, type = "success") => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => setToastMessage(null), 3000);
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
                View the status and details of your registered transactions here.
              </p>
              <footer className="blockquote-footer" style={{ fontSize: "0.7em" }}>
                Track your transactions securely and efficiently.
              </footer>
            </blockquote>
          </div>
        </div>
      </div>
      <div className="container" style={{marginTop: '-50px'}}>
        <h1 className="text-center mb-4" style={{fontFamily: 'Orbitron', fontSize: '1.5em'}}>Transaction Details</h1>
        <div className="card shadow p-4">
          <h3 className="card-title" style={{fontSize: '1.2em', textAlign: 'center'}}>Transactions for Address: <b>{address}</b></h3>
          <div className="card-body">
            {transactions.length === 0 ? (
              <p className="text-center text-muted">No transactions found for this address.</p>
            ) : (
              <table className="table table-striped">
                <thead>
                  <tr>
                    <th>TXID</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.txids}>
                      <td>
                        <button
                          className="btn btn-link p-0 d-flex align-items-center"
                          onClick={() => fetchTransactionDetails(tx.txids)}
                          style={{textDecoration: 'none', color: '#000000'}}
                        >
                          <BsSearch className="me-4" />
                          {tx.txids}
                        </button>
                      </td>
                      <td>{tx.amount} BTC</td>
                      <td>
                        <span
                          className={`badge ${
                            tx.status === "confirmed"
                              ? "bg-success"
                              : "bg-warning text-dark"
                          }`}
                        >
                          {tx.status || "pending"}
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
        {selectedTransaction && (
          <div className="card shadow p-4 mt-4">
            <h3 className="card-title" style={{fontFamily: 'Orbitron', fontSize: '1.2em'}}>
            Registration transaction details</h3>
            <div className="card-body">
              <p><strong>TXID:</strong> {selectedTransaction.txid}</p>
              <p><strong>Received By:</strong> {selectedTransaction.vout[0].scriptPubKey.address}</p>
              <p><strong>Amount:</strong> {selectedTransaction.vout[0].value} BTC</p>
              <p><strong>Status:</strong> 
                <span className={`badge ${selectedTransaction.status === "confirmed" ? "bg-success" : "bg-warning text-dark"}`}>
                  {selectedTransaction.status || "pending"}
                </span>
              </p>
              <p><strong>Date:</strong> {selectedTransaction.time
                ? new Date(selectedTransaction.time * 1000).toLocaleString("pt-BR", {
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
      {/* Estilos para centralizar o Toaster */}
      <style jsx global>{`
        .toaster-container {
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          z-index: 1050;
          width: 300px;
        }
      `}</style>
    </div>
  );
}