import React from "react";

function Header() {
 
  return (
    <div> 
      <link
          href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap"
          rel="stylesheet"
        />   
      <div className="text-center mb-4">      
        <img
          className="mb-3"
          src="/assets/imgs/logos/logo.png" 
          alt="Logo"
          style={{ 
            fontFamily: "Orbitron, sans-serif",
            width: "20vw",
            maxWidth: "150px",
            height: "auto" }}
        />
      </div>
      <h1 className="text-center mb-4" 
        style={{
        fontFamily: "Orbitron",
        fontSize: "1.5rem",
        fontWeight: "600",
        marginTop: "-30px", 
        color:"#2c3e50"
      }}
      >Doidos Descentralizados</h1>
      <h2 className="text-center mb-4" 
        style={{
          fontFamily: "Orbitron",
          fontSize: "1rem",
          fontWeight: "600",    
          marginTop: "-15px",  
          color:"black"
        }}
      >Blockchain Copyright Platform</h2>
    </div>
  );
}

export default Header;
