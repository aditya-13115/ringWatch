import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import AccountInvestigation from "./pages/AccountInvestigation";
import Rings from "./pages/Rings";
import About from "./pages/About";
import AuditLog from "./pages/AuditLog";
import Metrics from "./pages/Metrics";
import FailureDemo from "./pages/FailureDemo";
import AddressNormalization from "./pages/AddressNormalization";
import ErrorBoundary from "./components/ErrorBoundary";

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Landing />} />

          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/investigations/:accountId" element={<AccountInvestigation />} />
            <Route path="/rings" element={<Rings />} />
            <Route path="/about" element={<About />} />
            <Route path="/audit" element={<AuditLog />} />
            <Route path="/metrics" element={<Metrics />} />
            <Route path="/failure-demo" element={<FailureDemo />} />
            <Route path="/address-normalization" element={<AddressNormalization />} />
          </Route>
        </Routes>
      </ErrorBoundary>
    </BrowserRouter>
  );
}