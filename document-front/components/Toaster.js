import React from "react";

export default function Toaster({ message, type }) {
  if (!message) return null;

  const getBackgroundColor = () => {
    if (type === "success") return "bg-success text-white";
    if (type === "error") return "bg-danger text-white";
    return "bg-secondary text-white";
  };

  return (
    <div className={`toast-container position-fixed bottom-0 end-0 p-3`} style={{ zIndex: 1050 }}>
      <div className={`toast show ${getBackgroundColor()}`} role="alert">
        <div className="toast-body" style={{fontSize: '1.5em'}}>{message}</div>
      </div>
    </div>
  );
}
