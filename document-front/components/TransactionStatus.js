import { useState, useEffect } from "react";
import io from "socket.io-client";

const socket = io("http://localhost:5000");

export default function TransactionStatus({ txid }) {
  const [status, setStatus] = useState("pending");

  useEffect(() => {
    socket.on("payment_confirmed", (data) => {
      if (data.txid === txid) {
        setStatus("confirmed");
      }
    });
    return () => {
      socket.off("payment_confirmed");
    };
  }, [txid]);

  return (
    <div className={`p-4 rounded shadow-lg text-white ${status === "confirmed" ? "bg-green-500" : "bg-yellow-500"}`}>
      <p className="font-semibold"><b>Status da Transação:</b> {status}</p>
    </div>
  );
}
