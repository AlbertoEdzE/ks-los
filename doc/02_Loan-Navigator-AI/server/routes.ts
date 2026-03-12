import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { getChatResponse } from "./openai";
import { insertLoanProductCatalogSchema } from "@shared/schema";
import { z } from "zod";

const updateConversationSchema = z.object({
  status: z.enum(["active", "reviewing", "qualified", "archived"]).optional(),
  borrowerName: z.string().optional(),
  assignedOfficer: z.string().optional(),
  currentPhaseId: z.string().optional(),
});

const phaseActionSchema = z.object({
  action: z.enum(["add", "modify", "deactivate", "reactivate", "reorder"]),
  name: z.string().optional(),
  currentName: z.string().optional(),
  newName: z.string().optional(),
  description: z.string().optional(),
  afterPhase: z.string().optional(),
  color: z.string().optional(),
  icon: z.string().optional(),
});

const patchLoanSchema = z.object({
  borrowerName: z.string().optional(),
  borrowerEmail: z.string().nullable().optional(),
  borrowerPhone: z.string().nullable().optional(),
  loanType: z.string().optional(),
  loanAmount: z.string().optional(),
  interestRate: z.string().nullable().optional(),
  tenure: z.string().nullable().optional(),
  monthlyEmi: z.string().nullable().optional(),
  purpose: z.string().nullable().optional(),
  employmentType: z.string().nullable().optional(),
  monthlyIncome: z.string().nullable().optional(),
  existingDebts: z.string().nullable().optional(),
  creditScore: z.string().nullable().optional(),
  collateral: z.string().nullable().optional(),
  downPayment: z.string().nullable().optional(),
  propertyValue: z.string().nullable().optional(),
  ltv: z.string().nullable().optional(),
  currentPhaseId: z.string().nullable().optional(),
  status: z.string().optional(),
  notes: z.string().nullable().optional(),
});

const OFFICER_HEADER = "x-officer-role";
const OFFICER_TOKEN = "loan-officer-access";

function isOfficerRequest(req: any): boolean {
  return req.headers[OFFICER_HEADER] === OFFICER_TOKEN;
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.post("/api/conversations", async (req, res) => {
    try {
      const wantsOfficer = req.body?.chatRole === "officer";
      if (wantsOfficer && !isOfficerRequest(req)) {
        return res.status(403).json({ message: "Officer access required" });
      }
      const chatRole = wantsOfficer ? "officer" : "borrower";
      const phases = await storage.getActivePhases();

      const conversation = await storage.createConversation({
        status: "active",
        chatRole,
        currentPhaseId: chatRole === "borrower" && phases.length > 0 ? phases[0].id : undefined,
      });

      const greeting = await getChatResponse([], chatRole, phases, conversation.currentPhaseId);

      await storage.createMessage({
        conversationId: conversation.id,
        role: "assistant",
        content: greeting.response,
        metadata: greeting.intentAnalysis,
      });

      res.json({ conversation, greeting: greeting.response });
    } catch (error: any) {
      console.error("Error creating conversation:", error);
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/conversations", async (req, res) => {
    try {
      const allConversations = await storage.getAllConversations();
      res.json(allConversations);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/conversations/:id", async (req, res) => {
    try {
      const conversation = await storage.getConversation(req.params.id);
      if (!conversation) {
        return res.status(404).json({ message: "Conversation not found" });
      }
      res.json(conversation);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/conversations/:id/messages", async (req, res) => {
    try {
      const msgs = await storage.getMessagesByConversation(req.params.id);
      res.json(msgs);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/conversations/:id/messages", async (req, res) => {
    try {
      const { content } = req.body;
      if (!content) {
        return res.status(400).json({ message: "Content is required" });
      }

      const conversation = await storage.getConversation(req.params.id);
      if (!conversation) {
        return res.status(404).json({ message: "Conversation not found" });
      }

      await storage.createMessage({
        conversationId: req.params.id,
        role: "user",
        content,
      });

      const existingMessages = await storage.getMessagesByConversation(req.params.id);
      const history = existingMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const chatRole = (conversation.chatRole as "borrower" | "officer") || "borrower";
      const phases = await storage.getAllPhases();

      const { response, intentAnalysis, loanRecommendations, phaseAction, phaseUpdate, loanAction } = await getChatResponse(history, chatRole, phases, conversation.currentPhaseId);

      let phaseActionResult = null;
      if (phaseAction && chatRole === "officer" && isOfficerRequest(req)) {
        const parsed = phaseActionSchema.safeParse(phaseAction);
        if (parsed.success) {
          phaseActionResult = await executePhaseAction(parsed.data);
        } else {
          phaseActionResult = { success: false, message: "Invalid phase action format" };
        }
      }

      let loanActionResult = null;
      if (loanAction && chatRole === "officer" && isOfficerRequest(req)) {
        loanActionResult = await executeLoanAction(loanAction, req.params.id, phases);
      }

      const assistantMessage = await storage.createMessage({
        conversationId: req.params.id,
        role: "assistant",
        content: response,
        metadata: {
          intentAnalysis,
          loanRecommendations,
          phaseAction: phaseActionResult,
          loanAction: loanActionResult,
        },
      });

      const updateData: any = {};
      if (intentAnalysis) {
        updateData.intentSummary = intentAnalysis;
        if (intentAnalysis.seriousnessScore !== undefined) {
          updateData.seriousnessScore = intentAnalysis.seriousnessScore;
        }
        if (intentAnalysis.fitScore !== undefined) {
          updateData.fitScore = intentAnalysis.fitScore;
        }
        if (intentAnalysis.nextConversationAngle) {
          updateData.nextConversationAngle = intentAnalysis.nextConversationAngle;
        }
      }
      if (loanRecommendations) {
        updateData.recommendedProducts = loanRecommendations;
      }
      if (phaseUpdate?.phaseId && chatRole === "borrower") {
        const activePhases = phases.filter(p => p.isActive).sort((a, b) => a.sortOrder - b.sortOrder);
        const currentIdx = conversation.currentPhaseId
          ? activePhases.findIndex(p => p.id === conversation.currentPhaseId)
          : -1;
        const targetIdx = activePhases.findIndex(p => p.id === phaseUpdate.phaseId);
        if (targetIdx >= 0 && targetIdx === currentIdx + 1) {
          updateData.currentPhaseId = phaseUpdate.phaseId;
        }
      }

      if (Object.keys(updateData).length > 0) {
        await storage.updateConversation(req.params.id, updateData);
      }

      res.json({
        message: assistantMessage,
        intentAnalysis,
        loanRecommendations,
        phaseAction: phaseActionResult,
        loanAction: loanActionResult,
      });
    } catch (error: any) {
      console.error("Error sending message:", error);
      res.status(500).json({ message: error.message });
    }
  });

  app.patch("/api/conversations/:id", async (req, res) => {
    try {
      const parsed = updateConversationSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid update data", errors: parsed.error.errors });
      }
      const conversation = await storage.getConversation(req.params.id);
      if (!conversation) {
        return res.status(404).json({ message: "Conversation not found" });
      }
      const updated = await storage.updateConversation(req.params.id, parsed.data);
      res.json(updated);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/phases", async (_req, res) => {
    try {
      const phases = await storage.getAllPhases();
      res.json(phases);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/phases/active", async (_req, res) => {
    try {
      const phases = await storage.getActivePhases();
      res.json(phases);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/loans", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const allLoans = await storage.getAllLoans();
      res.json(allLoans);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/loans/:id", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const loan = await storage.getLoan(req.params.id);
      if (!loan) return res.status(404).json({ message: "Loan not found" });
      res.json(loan);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.patch("/api/loans/:id", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const loan = await storage.getLoan(req.params.id);
      if (!loan) return res.status(404).json({ message: "Loan not found" });
      const parsed = patchLoanSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid loan update data", errors: parsed.error.errors });
      }
      const updated = await storage.updateLoan(req.params.id, parsed.data);
      res.json(updated);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/catalog-products", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const products = await storage.getAllCatalogProducts();
      res.json(products);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.get("/api/catalog-products/:id", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const product = await storage.getCatalogProduct(req.params.id);
      if (!product) return res.status(404).json({ message: "Product not found" });
      res.json(product);
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  app.post("/api/catalog-products", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const parsed = insertLoanProductCatalogSchema.safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid product data", errors: parsed.error.errors });
      }
      const product = await storage.createCatalogProduct(parsed.data);
      res.status(201).json(product);
    } catch (error: any) {
      if (error.message?.includes("duplicate key") || error.code === "23505") {
        return res.status(409).json({ message: "A product with this code already exists." });
      }
      res.status(500).json({ message: error.message });
    }
  });

  app.patch("/api/catalog-products/:id", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const product = await storage.getCatalogProduct(req.params.id);
      if (!product) return res.status(404).json({ message: "Product not found" });
      const parsed = insertLoanProductCatalogSchema.partial().safeParse(req.body);
      if (!parsed.success) {
        return res.status(400).json({ message: "Invalid product data", errors: parsed.error.errors });
      }
      const updated = await storage.updateCatalogProduct(req.params.id, parsed.data);
      res.json(updated);
    } catch (error: any) {
      if (error.message?.includes("duplicate key") || error.code === "23505") {
        return res.status(409).json({ message: "A product with this code already exists." });
      }
      res.status(500).json({ message: error.message });
    }
  });

  app.delete("/api/catalog-products/:id", async (req, res) => {
    if (!isOfficerRequest(req)) {
      return res.status(403).json({ message: "Officer access required" });
    }
    try {
      const product = await storage.getCatalogProduct(req.params.id);
      if (!product) return res.status(404).json({ message: "Product not found" });
      await storage.deleteCatalogProduct(req.params.id);
      res.json({ success: true });
    } catch (error: any) {
      res.status(500).json({ message: error.message });
    }
  });

  return httpServer;
}

async function executePhaseAction(action: any): Promise<{ success: boolean; message: string; phase?: any }> {
  try {
    switch (action.action) {
      case "add": {
        const existing = await storage.getPhaseByName(action.name);
        if (existing && existing.isActive) {
          return { success: false, message: `Phase "${action.name}" already exists.` };
        }
        if (existing && !existing.isActive) {
          const reactivated = await storage.updatePhase(existing.id, {
            isActive: true,
            name: action.name,
            description: action.description || existing.description,
            color: action.color || existing.color,
          });
          return { success: true, message: `Phase "${action.name}" was previously deactivated and has been reactivated.`, phase: reactivated };
        }

        let sortOrder: number;
        if (action.afterPhase === "start") {
          const allPhases = await storage.getActivePhases();
          for (const p of allPhases) {
            await storage.updatePhase(p.id, { sortOrder: p.sortOrder + 1 });
          }
          sortOrder = 1;
        } else if (action.afterPhase === "end" || !action.afterPhase) {
          sortOrder = (await storage.getMaxSortOrder()) + 1;
        } else {
          const afterPhase = await storage.getPhaseByName(action.afterPhase);
          if (!afterPhase) {
            sortOrder = (await storage.getMaxSortOrder()) + 1;
          } else {
            const allPhases = await storage.getAllPhases();
            for (const p of allPhases) {
              if (p.sortOrder > afterPhase.sortOrder) {
                await storage.updatePhase(p.id, { sortOrder: p.sortOrder + 1 });
              }
            }
            sortOrder = afterPhase.sortOrder + 1;
          }
        }

        const phase = await storage.createPhase({
          name: action.name,
          description: action.description || null,
          sortOrder,
          isActive: true,
          color: action.color || "#2dd4bf",
          icon: action.icon || "circle",
        });
        return { success: true, message: `Phase "${action.name}" added successfully at position ${sortOrder}.`, phase };
      }

      case "modify": {
        const phase = await storage.getPhaseByName(action.currentName);
        if (!phase) {
          return { success: false, message: `Phase "${action.currentName}" not found.` };
        }
        const updateData: any = {};
        if (action.newName) updateData.name = action.newName;
        if (action.description) updateData.description = action.description;
        if (action.color) updateData.color = action.color;
        const updated = await storage.updatePhase(phase.id, updateData);
        return { success: true, message: `Phase "${action.currentName}" updated successfully.`, phase: updated };
      }

      case "deactivate": {
        const phase = await storage.getPhaseByName(action.name);
        if (!phase) {
          return { success: false, message: `Phase "${action.name}" not found.` };
        }
        if (!phase.isActive) {
          return { success: false, message: `Phase "${action.name}" is already deactivated.` };
        }
        const deactivated = await storage.deactivatePhase(phase.id);
        return { success: true, message: `Phase "${action.name}" has been deactivated (soft-deleted). It can be reactivated later.`, phase: deactivated };
      }

      case "reactivate": {
        const phase = await storage.getPhaseByName(action.name);
        if (!phase) {
          return { success: false, message: `Phase "${action.name}" not found.` };
        }
        if (phase.isActive) {
          return { success: false, message: `Phase "${action.name}" is already active.` };
        }
        const reactivated = await storage.updatePhase(phase.id, { isActive: true });
        return { success: true, message: `Phase "${action.name}" has been reactivated.`, phase: reactivated };
      }

      case "reorder": {
        const phase = await storage.getPhaseByName(action.name);
        if (!phase) {
          return { success: false, message: `Phase "${action.name}" not found.` };
        }
        const allPhases = await storage.getActivePhases();
        const filtered = allPhases.filter(p => p.id !== phase.id);

        let insertIdx: number;
        if (action.afterPhase === "start") {
          insertIdx = 0;
        } else {
          const afterPhase = filtered.find(p => p.name.toLowerCase() === action.afterPhase?.toLowerCase());
          if (!afterPhase) {
            insertIdx = filtered.length;
          } else {
            insertIdx = filtered.indexOf(afterPhase) + 1;
          }
        }

        filtered.splice(insertIdx, 0, phase);
        const ids = filtered.map(p => p.id);
        await storage.reorderPhases(ids);
        return { success: true, message: `Phase "${action.name}" moved successfully.`, phase };
      }

      default:
        return { success: false, message: `Unknown action: ${action.action}` };
    }
  } catch (error: any) {
    console.error("Phase action error:", error);
    return { success: false, message: `Error executing phase action: ${error.message}` };
  }
}

async function executeLoanAction(action: any, conversationId: string, phases: any[]): Promise<{ success: boolean; message: string; loan?: any }> {
  try {
    if (action.action === "create") {
      const activePhases = phases.filter(p => p.isActive).sort((a: any, b: any) => a.sortOrder - b.sortOrder);
      const firstPhaseId = activePhases.length > 0 ? activePhases[0].id : null;

      const loan = await storage.createLoan({
        borrowerName: action.borrowerName || "Unknown",
        borrowerEmail: action.borrowerEmail || null,
        borrowerPhone: action.borrowerPhone || null,
        loanType: action.loanType || "Personal Loan",
        loanAmount: action.loanAmount || "Not specified",
        interestRate: action.interestRate || null,
        tenure: action.tenure || null,
        monthlyEmi: action.monthlyEmi || null,
        purpose: action.purpose || null,
        employmentType: action.employmentType || null,
        monthlyIncome: action.monthlyIncome || null,
        existingDebts: action.existingDebts || null,
        creditScore: action.creditScore || null,
        collateral: action.collateral || null,
        downPayment: action.downPayment || null,
        propertyValue: action.propertyValue || null,
        ltv: action.ltv || null,
        currentPhaseId: firstPhaseId,
        status: "draft",
        notes: action.notes || null,
        conversationId,
        createdBy: "officer",
      });

      return { success: true, message: `Loan application created for ${loan.borrowerName} (${loan.loanType} — ${loan.loanAmount}).`, loan };
    } else if (action.action === "update") {
      const loan = await storage.getLoan(action.loanId);
      if (!loan) {
        return { success: false, message: `Loan with ID "${action.loanId}" not found.` };
      }
      const updated = await storage.updateLoan(action.loanId, action.updates || {});
      return { success: true, message: `Loan for ${updated.borrowerName} updated successfully.`, loan: updated };
    }

    return { success: false, message: `Unknown loan action: ${action.action}` };
  } catch (error: any) {
    console.error("Loan action error:", error);
    return { success: false, message: `Error executing loan action: ${error.message}` };
  }
}
