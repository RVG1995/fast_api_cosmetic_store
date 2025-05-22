import React from "react";
import BoxberryFunnelAdminBlock from "../../components/admin/BoxberryFunnelAdminBlock";

export default function AdminBoxberryFunnel() {
  return (
    <div className="container py-4">
      <h2 className="mb-4">Воронка статусов Boxberry → статусы заказа</h2>
      <BoxberryFunnelAdminBlock />
    </div>
  );
} 