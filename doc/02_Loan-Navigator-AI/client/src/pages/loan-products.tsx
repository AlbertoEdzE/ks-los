import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { OFFICER_HEADERS } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-provider";
import {
  Plus,
  Search,
  ArrowLeft,
  CheckCircle2,
  FileText,
  Layers,
  Package,
} from "lucide-react";
import { Link } from "wouter";
import type { CatalogProduct } from "@shared/schema";
import ksqLogo from "@assets/image_1773224776245.png";
import { CATEGORIES, STATUSES } from "@/components/products/constants";
import { ProductForm } from "@/components/products/product-form";
import { ProductCard } from "@/components/products/product-card";
import { ProductDetail } from "@/components/products/product-detail";

export default function LoanProductsPage() {
  const [showForm, setShowForm] = useState(false);
  const [editProduct, setEditProduct] = useState<CatalogProduct | null>(null);
  const [viewProduct, setViewProduct] = useState<CatalogProduct | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const productsQuery = useQuery<CatalogProduct[]>({
    queryKey: ["/api/catalog-products"],
    queryFn: async () => {
      const res = await fetch("/api/catalog-products", { headers: OFFICER_HEADERS });
      if (!res.ok) throw new Error("Failed to fetch products");
      return res.json();
    },
  });

  const products = productsQuery.data || [];

  const filtered = products.filter(p => {
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase()) && !p.code.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (filterCategory !== "all" && p.category !== filterCategory) return false;
    if (filterStatus !== "all" && p.status !== filterStatus) return false;
    return true;
  });

  const activeCount = products.filter(p => p.status === "active").length;
  const draftCount = products.filter(p => p.status === "draft").length;
  const categoryCount = new Set(products.map(p => p.category)).size;

  const inputCls = "w-full text-sm text-slate-800 dark:text-slate-100 bg-white dark:bg-white/[0.04] border-0 ring-1 ring-slate-200/60 dark:ring-white/[0.06] rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/20 placeholder:text-slate-300 dark:placeholder:text-slate-600 transition-all";

  return (
    <div className="flex flex-col h-screen bg-[#f8f9fb] dark:bg-[#0e1015] relative overflow-hidden">
      <div className="absolute top-[-200px] right-[-100px] w-[600px] h-[600px] bg-blue-200/20 dark:bg-blue-500/[0.03] rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute bottom-[-150px] left-[-50px] w-[400px] h-[400px] bg-indigo-200/15 dark:bg-indigo-500/[0.02] rounded-full blur-[120px] pointer-events-none" />

      <header className="relative z-10 border-b border-slate-200/40 dark:border-white/[0.04] px-6 py-4 flex items-center justify-between bg-white/80 dark:bg-[#12141a]/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <Link href="/dashboard">
            <Button variant="ghost" size="icon" className="rounded-xl text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/[0.06]">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div className="w-10 h-10 rounded-xl bg-white dark:bg-white/10 flex items-center justify-center shadow-sm">
            <img src={ksqLogo} alt="KSquare" className="w-7 h-7 object-contain dark:brightness-0 dark:invert" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-slate-800 dark:text-white" data-testid="text-products-title">Loan Product Catalog</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500">Configure and manage lending products</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button
            data-testid="button-new-product"
            onClick={() => setShowForm(true)}
            className="gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg shadow-blue-600/20 dark:shadow-blue-900/40 border-0"
          >
            <Plus className="w-4 h-4" />
            New Product
          </Button>
        </div>
      </header>

      <div className="relative z-10 grid grid-cols-4 gap-4 p-6 pb-0">
        {[
          { value: products.length, label: "Total Products", icon: Package, gradient: "from-blue-500 to-blue-600", testId: "text-stat-total" },
          { value: activeCount, label: "Active", icon: CheckCircle2, gradient: "from-emerald-500 to-emerald-600" },
          { value: draftCount, label: "Drafts", icon: FileText, gradient: "from-amber-500 to-amber-600" },
          { value: categoryCount, label: "Categories", icon: Layers, gradient: "from-indigo-500 to-indigo-600" },
        ].map((stat, i) => (
          <div key={i} className="bg-white dark:bg-[#161820] rounded-2xl ring-1 ring-black/[0.03] dark:ring-white/[0.04] shadow-sm p-4 flex items-center gap-3.5">
            <div className={`p-2.5 rounded-xl bg-gradient-to-br ${stat.gradient} text-white shadow-sm`}>
              <stat.icon className="w-4 h-4" />
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-800 dark:text-white" data-testid={stat.testId}>{stat.value}</p>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="relative z-10 px-6 pt-4 flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-300 dark:text-slate-600" />
          <input
            data-testid="input-search-products"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search by name or code..."
            className={`${inputCls} pl-9`}
          />
        </div>
        <select
          data-testid="filter-category"
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className={`${inputCls} w-48`}
        >
          <option value="all">All Categories</option>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select
          data-testid="filter-status"
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className={`${inputCls} w-36`}
        >
          <option value="all">All Status</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
        </select>
      </div>

      <div className="flex-1 relative z-10 overflow-y-auto p-6 pt-4">
        {productsQuery.isLoading ? (
          <div className="grid grid-cols-3 gap-5">
            {Array(6).fill(0).map((_, i) => (
              <div key={i} className="h-64 rounded-2xl bg-slate-100 dark:bg-white/[0.04] animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-20 h-20 rounded-2xl bg-slate-50 dark:bg-white/[0.04] flex items-center justify-center mb-5 shadow-sm ring-1 ring-black/[0.03] dark:ring-white/[0.04]">
              <Package className="w-9 h-9 text-slate-200 dark:text-slate-700" />
            </div>
            <h3 className="font-semibold text-lg mb-1.5 text-slate-700 dark:text-white">
              {products.length === 0 ? "No Products Yet" : "No Matching Products"}
            </h3>
            <p className="text-sm text-slate-400 dark:text-slate-500 max-w-xs mb-4">
              {products.length === 0
                ? "Create your first loan product to start building your lending catalog."
                : "Try adjusting your search or filters."}
            </p>
            {products.length === 0 && (
              <Button
                onClick={() => setShowForm(true)}
                className="rounded-xl gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white border-0"
              >
                <Plus className="w-4 h-4" />
                Create First Product
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map(product => (
              <ProductCard
                key={product.id}
                product={product}
                onEdit={() => setEditProduct(product)}
                onView={() => setViewProduct(product)}
              />
            ))}
          </div>
        )}
      </div>

      {showForm && (
        <ProductForm isNew onClose={() => setShowForm(false)} />
      )}
      {editProduct && (
        <ProductForm product={editProduct} isNew={false} onClose={() => setEditProduct(null)} />
      )}
      {viewProduct && (
        <ProductDetail
          product={viewProduct}
          onClose={() => setViewProduct(null)}
          onEdit={() => { setEditProduct(viewProduct); setViewProduct(null); }}
        />
      )}
    </div>
  );
}
