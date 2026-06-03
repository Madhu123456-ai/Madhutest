import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import StatsCards from './components/StatsCards';
import ProductSearch from './components/ProductSearch';
import Cart, { useCartTotals } from './components/Cart';
import CustomerPanel from './components/CustomerPanel';
import RecentQuotations from './components/RecentQuotations';
import ConfirmModal from './components/ConfirmModal';
import {
  fetchStats,
  fetchCompany,
  fetchQuotations,
  saveQuotation,
} from './utils/api';
import { generateQuotationPdf } from './utils/pdf';
import { initiatePayment } from './utils/payment';

const emptyCustomer = {
  name: '',
  phone: '',
  email: '',
  address: '',
};

export default function App() {
  const [stats, setStats] = useState(null);
  const [company, setCompany] = useState(null);
  const [cart, setCart] = useState([]);
  const [customer, setCustomer] = useState(emptyCustomer);
  const [quotations, setQuotations] = useState([]);
  const [showConfirm, setShowConfirm] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [toast, setToast] = useState(null);

  const gstRate = company?.gstRate ?? 18;
  const { subtotal, gst, total } = useCartTotals(cart, gstRate);

  const loadData = useCallback(async () => {
    const [s, c, q] = await Promise.all([
      fetchStats(),
      fetchCompany(),
      fetchQuotations(),
    ]);
    setStats(s);
    setCompany(c);
    setQuotations(q);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const addToCart = (tree) => {
    setCart((prev) => {
      const existing = prev.find((i) => i.id === tree.id);
      if (existing) {
        return prev.map((i) =>
          i.id === tree.id ? { ...i, qty: i.qty + 1 } : i
        );
      }
      return [...prev, { ...tree, qty: 1 }];
    });
    showToast(`${tree.name} added to cart`);
  };

  const updateQty = (id, qty) => {
    setCart((prev) => prev.map((i) => (i.id === id ? { ...i, qty } : i)));
  };

  const removeFromCart = (id) => {
    setCart((prev) => prev.filter((i) => i.id !== id));
  };

  const buildQuotationPayload = (status) => ({
    customer,
    items: cart.map((i) => ({
      name: i.name,
      qty: i.qty,
      price: i.price,
      total: i.price * i.qty,
    })),
    subtotal,
    gst,
    total,
    status,
  });

  const validate = () => {
    if (cart.length < 1) {
      showToast('Please add at least one tree to the cart');
      return false;
    }
    if (!customer.name.trim()) {
      showToast('Please enter customer name');
      return false;
    }
    return true;
  };

  const handleContinue = () => {
    if (!validate()) return;
    setPendingAction('generate');
    setShowConfirm(true);
  };

  const handleConfirmGenerate = async () => {
    setShowConfirm(false);
    if (!validate()) return;

    const saved = await saveQuotation(
      buildQuotationPayload('Sent')
    );
    const quotation = { ...saved, customer, items: buildQuotationPayload().items, subtotal, gst, total };
    generateQuotationPdf(quotation, company);
    showToast(`Quotation ${saved.id} generated & downloaded`);
    await loadData();
    setPendingAction(null);
  };

  const handleGeneratePdf = async () => {
    if (!validate()) return;
    const saved = await saveQuotation(buildQuotationPayload('Sent'));
    const quotation = {
      ...saved,
      customer,
      items: buildQuotationPayload().items,
      subtotal,
      gst,
      total,
    };
    generateQuotationPdf(quotation, company);
    showToast(`PDF downloaded for ${saved.id}`);
    await loadData();
  };

  const handlePayment = async () => {
    if (!validate()) return;
    const saved = await saveQuotation(buildQuotationPayload('Draft'));
    await initiatePayment(
      total,
      saved.id,
      async () => {
        showToast(`Payment successful for ${saved.id}`);
        await loadData();
      },
      (err) => showToast(err || 'Payment failed')
    );
  };

  const handleSaveDraft = async () => {
    if (cart.length < 1) {
      showToast('Add items before saving draft');
      return;
    }
    const saved = await saveQuotation(buildQuotationPayload('Draft'));
    showToast(`Draft saved as ${saved.id}`);
    await loadData();
  };

  const handleClearAll = () => {
    setCart([]);
    setCustomer(emptyCustomer);
    showToast('Cart and customer cleared');
  };

  const handleCustomerChange = (key, value) => {
    setCustomer((prev) => ({ ...prev, [key]: value }));
  };

  const cartDisabled = cart.length === 0 || !customer.name.trim();

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Header />

        <main className="flex-1 p-6 overflow-y-auto">
          <StatsCards stats={stats} />

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-4">
              <ProductSearch onAdd={addToCart} />
            </div>
            <div className="lg:col-span-5">
              <Cart
                items={cart}
                gstRate={gstRate}
                onUpdateQty={updateQty}
                onRemove={removeFromCart}
                onClear={() => setCart([])}
                onContinue={handleContinue}
              />
            </div>
            <div className="lg:col-span-3">
              <CustomerPanel
                customer={customer}
                onChange={handleCustomerChange}
                onSaveCustomer={() =>
                  showToast('Customer details saved locally')
                }
                onGeneratePdf={handleGeneratePdf}
                onPayment={handlePayment}
                onSaveDraft={handleSaveDraft}
                onClearAll={handleClearAll}
                disabled={cartDisabled}
              />
            </div>
          </div>

          <RecentQuotations quotations={quotations} onRefresh={loadData} />
        </main>
      </div>

      <ConfirmModal
        open={showConfirm}
        title="Generate Quotation?"
        message={`You have ${cart.length} item(s) totaling ₹${total.toFixed(2)}. Generate a PDF quotation with company logo, address, and customer details?`}
        onConfirm={
          pendingAction === 'generate'
            ? handleConfirmGenerate
            : () => setShowConfirm(false)
        }
        onCancel={() => setShowConfirm(false)}
      />

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#1a5c2e] text-white px-4 py-3 rounded-lg shadow-lg text-sm animate-pulse">
          {toast}
        </div>
      )}
    </div>
  );
}
