import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/theme-provider";
import NotFound from "@/pages/not-found";
import ChatPage from "@/pages/chat";
import OfficerDashboard from "@/pages/officer-dashboard";
import OfficerChat from "@/pages/officer-chat";
import LoanProducts from "@/pages/loan-products";
import PhaseDetail from "@/pages/phase-detail";
import LoanPipeline from "@/pages/loan-pipeline";

function Router() {
  return (
    <Switch>
      <Route path="/" component={ChatPage} />
      <Route path="/dashboard" component={OfficerDashboard} />
      <Route path="/officer-chat" component={OfficerChat} />
      <Route path="/loan-products" component={LoanProducts} />
      <Route path="/phases/:id" component={PhaseDetail} />
      <Route path="/pipeline" component={LoanPipeline} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

export default App;
