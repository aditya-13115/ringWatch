import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import AccountInvestigation from "./pages/AccountInvestigation";
import AuditLog from "./pages/AuditLog";
import Metrics from "./pages/Metrics";
import FailureDemo from "./pages/FailureDemo";
import AddressNormalization from "./pages/AddressNormalization";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/investigations/:accountId" element={<AccountInvestigation />} />
          <Route path="/audit" element={<AuditLog />} />
          <Route path="/metrics" element={<Metrics />} />
          <Route path="/failure-demo" element={<FailureDemo />} />
          <Route path="/address-normalization" element={<AddressNormalization />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}