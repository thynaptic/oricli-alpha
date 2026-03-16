package api

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/bus"
	"github.com/thynaptic/oricli-go/pkg/service"
)

// Server represents the Go API Gateway
type Server struct {
	Router       *gin.Engine
	Orchestrator *service.GoOrchestrator
	Agent        *service.GoAgentService
	Monitor      *service.MonitorService
	Goals        *service.GoalService
	Profiles     *service.AgentProfileService
	Subconscious *service.SubconsciousService
	Rules        *service.RulesEngine
	Skills       *service.SkillManager
	Budget       *service.BudgetManager
	Insights     *service.InsightService
	Precog       *service.PrecogService
	Absorption   *service.AbsorptionService
	Coordinator  *service.AgentCoordinator
	Pipeline     *service.MultiAgentPipelineService
	ReasoningOrch *service.CognitiveOrchestrator
	ConvOrch      *service.ConversationalOrchestrator
	Knowledge     *service.WorldKnowledgeService
	CodeReview    *service.CodeReviewService
	ProjectUnder  *service.ProjectUnderstandingService
	CodeMetrics   *service.CodeMetricsService
	Security      *service.SecurityAnalysisService
	DocGen        *service.DocumentationGeneratorService
	SemanticUnder *service.SemanticUnderstandingService
	ThoughtToText *service.ThoughtToTextService
	Emotion       *service.EmotionalInferenceService
	Refactoring   *service.RefactoringService
	Search        *service.CodebaseSearchService
	Explain       *service.CodeExplanationService
	Migration     *service.MigrationAssistantService
	Style         *service.StyleAdaptationService
	Learning      *service.LearningSystemService
	CodeMemory    *service.CodeMemoryService
	Embeddings    *service.CodeEmbeddingsService
	Metrics       *service.MetricsCollector
	TraceStore    *service.TraceStore
	Health        *service.ModuleHealthDiagnosticsService
	ReasoningStrat *service.ReasoningStrategyService
	Document      *service.DocumentService
	Port          int
}

func NewServer(orch *service.GoOrchestrator, agent *service.GoAgentService, mon *service.MonitorService, goals *service.GoalService, profiles *service.AgentProfileService, subconscious *service.SubconsciousService, rules *service.RulesEngine, skills *service.SkillManager, budget *service.BudgetManager, insights *service.InsightService, precog *service.PrecogService, absorption *service.AbsorptionService, coordinator *service.AgentCoordinator, pipeline *service.MultiAgentPipelineService, reasoningOrch *service.CognitiveOrchestrator, convOrch *service.ConversationalOrchestrator, knowledge *service.WorldKnowledgeService, codeReview *service.CodeReviewService, projectUnder *service.ProjectUnderstandingService, codeMetrics *service.CodeMetricsService, security *service.SecurityAnalysisService, docGen *service.DocumentationGeneratorService, semanticUnder *service.SemanticUnderstandingService, thoughtToText *service.ThoughtToTextService, emotion *service.EmotionalInferenceService, refactoring *service.RefactoringService, search *service.CodebaseSearchService, explain *service.CodeExplanationService, migration *service.MigrationAssistantService, style *service.StyleAdaptationService, learning *service.LearningSystemService, codeMemory *service.CodeMemoryService, embeddings *service.CodeEmbeddingsService, metrics *service.MetricsCollector, traces *service.TraceStore, health *service.ModuleHealthDiagnosticsService, reasoningStrat *service.ReasoningStrategyService, doc *service.DocumentService, port int) *Server {
	// Set Gin to release mode if not in development
	if os.Getenv("GO_ENV") == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	r := gin.Default()

	// Middleware for logging and recovery
	r.Use(gin.Logger())
	r.Use(gin.Recovery())

	s := &Server{
		Router:       r,
		Orchestrator: orch,
		Agent:        agent,
		Monitor:      mon,
		Goals:        goals,
		Profiles:     profiles,
		Subconscious: subconscious,
		Rules:        rules,
		Skills:       skills,
		Budget:       budget,
		Insights:     insights,
		Precog:       precog,
		Absorption:   absorption,
		Coordinator:  coordinator,
		Pipeline:     pipeline,
		ReasoningOrch: reasoningOrch,
		ConvOrch:      convOrch,
		Knowledge:     knowledge,
		CodeReview:    codeReview,
		ProjectUnder:  projectUnder,
		CodeMetrics:   codeMetrics,
		Security:      security,
		DocGen:        docGen,
		SemanticUnder: semanticUnder,
		ThoughtToText: thoughtToText,
		Emotion:       emotion,
		Refactoring:   refactoring,
		Search:        search,
		Explain:       explain,
		Migration:     migration,
		Style:         style,
		Learning:      learning,
		CodeMemory:    codeMemory,
		Embeddings:    embeddings,
		Metrics:      metrics,
		TraceStore:   traces,
		Health:        health,
		ReasoningStrat: reasoningStrat,
		Document:      doc,
		Port:         port,
	}

	s.setupRoutes()
	return s
}

func (s *Server) setupRoutes() {
	v1 := s.Router.Group("/v1")
	{
		// OpenAI Compatible Endpoints
		v1.POST("/chat/completions", s.handleChatCompletions)
		v1.POST("/embeddings", s.handleEmbeddings)
		v1.GET("/models", s.handleListModels)

		// Sovereign Hive Endpoints
		v1.POST("/swarm/run", s.handleSwarmRun)
		v1.POST("/swarm/inject", s.handleSwarmInject)
		
		// Sovereign Goals
		v1.GET("/goals", s.handleListGoals)
		v1.POST("/goals", s.handleCreateGoal)
		v1.GET("/goals/:id", s.handleGetGoal)

		// Agent Factory
		v1.GET("/agents", s.handleListAgents)
		v1.POST("/agents", s.handleCreateAgent)
		v1.PUT("/agents/:name", s.handleUpdateAgent)
		v1.DELETE("/agents/:name", s.handleDeleteAgent)

		// Skills & Rules
		v1.GET("/skills", s.handleListSkills)
		v1.GET("/skills/:name", s.handleGetSkill)
		v1.POST("/skills", s.handleCreateSkill)
		v1.PUT("/skills/:name", s.handleUpdateSkill)
		v1.DELETE("/skills/:name", s.handleDeleteSkill)

		v1.GET("/rules", s.handleListRules)
		v1.GET("/rules/:name", s.handleGetRule)
		v1.POST("/rules", s.handleCreateRule)
		v1.PUT("/rules/:name", s.handleUpdateRule)
		v1.DELETE("/rules/:name", s.handleDeleteRule)

		// Ingestion API
		v1.POST("/ingest", s.handleIngest)
		v1.POST("/ingest/web", s.handleIngestWeb)

		// Knowledge Graph
		v1.POST("/knowledge/extract", s.handleKnowledgeExtract)
		v1.POST("/knowledge/query", s.handleKnowledgeQuery)
		v1.GET("/knowledge/world/query", s.handleWorldKnowledgeQuery)
		v1.POST("/knowledge/world/add", s.handleWorldKnowledgeAdd)

		// Code Analysis
		v1.POST("/code/review", s.handleCodeReview)
		v1.POST("/code/score", s.handleCodeScore)
		v1.POST("/code/metrics", s.handleCodeMetrics)
		v1.POST("/code/complexity", s.handleCodeComplexity)
		v1.POST("/code/security/analyze", s.handleCodeSecurityAnalyze)

		// Refactoring
		v1.POST("/code/refactor/suggest", s.handleRefactorSuggest)

		// Codebase Search
		v1.POST("/codebase/search", s.handleCodebaseSearch)

		// Migration
		v1.POST("/code/migrate/plan", s.handleMigratePlan)
		v1.POST("/code/migrate/execute", s.handleMigrateExecute)

		// Style Adaptation
		v1.POST("/code/style/detect", s.handleStyleDetect)
		v1.POST("/code/style/adapt", s.handleStyleAdapt)

		// Learning System
		v1.POST("/code/learning/correction", s.handleLearningCorrection)
		v1.POST("/code/learning/personalize", s.handleLearningPersonalize)

		// Code Memory
		v1.POST("/code/memory/remember", s.handleCodeMemoryRemember)
		v1.POST("/code/memory/recall", s.handleCodeMemoryRecall)

		// Code Embeddings
		v1.POST("/code/embeddings/generate", s.handleEmbedCode)
		v1.POST("/code/embeddings/similar", s.handleSimilarCode)

		// Project Understanding
		v1.POST("/project/understand", s.handleProjectUnderstand)

		// Documentation
		v1.POST("/code/documentation/docstring", s.handleGenerateDocstring)
		v1.POST("/project/documentation/readme", s.handleGenerateReadme)
		v1.POST("/code/explain", s.handleExplainCode)

		// Documents
		v1.POST("/documents/analyze", s.handleAnalyzeDocument)

		// Semantic Understanding
		v1.POST("/code/semantics/analyze", s.handleCodeSemanticsAnalyze)

		// Emotion
		v1.POST("/emotion/score", s.handleEmotionScore)
		v1.POST("/emotion/warmth", s.handleEmotionWarmth)

		// Reasoning
		v1.POST("/reasoning/code", s.handleReasoningCode)
		v1.POST("/reasoning/flow", s.handleReasoningFlow)
		v1.POST("/reasoning/thought_graph", s.handleConvertThoughtGraph)
		v1.POST("/reasoning/thought_tree", s.handleConvertReasoningTree)

		// Pipeline
		v1.POST("/pipeline/run", s.handlePipelineRun)

		// Conversational
		v1.POST("/conversational/response", s.handleConversationalResponse)

		// Subconscious
		v1.GET("/subconscious/mental_state", s.handleGetMentalState)

		// Budget
		v1.GET("/budget/balance", s.handleGetBudgetBalance)

		// Insights
		v1.GET("/insights/untrained", s.handleListUntrainedInsights)

		// Precog
		v1.POST("/precog/cache", s.handleCachePrecog)
		v1.GET("/precog/get", s.handleGetPrecog)

		// Absorption
		v1.GET("/absorption/count", s.handleGetAbsorptionCount)

		// Metrics & Traces
		v1.GET("/metrics", s.handleGetMetrics)
		v1.GET("/traces", s.handleGetTraces)

		// Health Checks
		v1.GET("/health", func(c *gin.Context) {
			c.JSON(http.StatusOK, gin.H{"status": "ready", "system": "oricli-go-gateway"})
		})
		v1.GET("/health/modules", func(c *gin.Context) {
			c.JSON(http.StatusOK, s.Monitor.ListStatuses())
		})
		v1.GET("/health/detailed", s.handleDetailedHealth)
	}

	// Ollama-style API Aliases
	s.Router.POST("/api/generate", s.handleOllamaGenerate)
	s.Router.POST("/api/chat", s.handleOllamaChat)
	s.Router.GET("/api/tags", s.handleOllamaTags)
}

// ... (previous handlers remain unchanged)

func (s *Server) handleEmbeddings(c *gin.Context) {
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	// Route to the embeddings module via Orchestrator
	result, err := s.Orchestrator.Execute("embeddings", req, 30*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleIngest(c *gin.Context) {
	// Support both JSON and Multipart
	var result interface{}
	var err error

	if strings.Contains(c.GetHeader("Content-Type"), "multipart/form-data") {
		file, _ := c.FormFile("file")
		text := c.PostForm("text")
		source := c.PostForm("source")
		if source == "" { source = "direct_ingestion" }
		
		params := map[string]interface{}{
			"source": source,
			"metadata": map[string]interface{}{
				"tags": c.PostForm("tags"),
				"domain": c.PostForm("domain"),
			},
		}

		if file != nil {
			params["file_name"] = file.Filename
			params["mime_type"] = file.Header.Get("Content-Type")
			// In a real scenario, we'd read the file content here
			// For now, route to ingestion_agent
			result, err = s.Orchestrator.Execute("ingest_file", params, 60*time.Second)
		} else {
			params["text"] = text
			result, err = s.Orchestrator.Execute("ingest_text", params, 60*time.Second)
		}
	} else {
		var req map[string]interface{}
		c.ShouldBindJSON(&req)
		result, err = s.Orchestrator.Execute("ingest_text", req, 60*time.Second)
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleIngestWeb(c *gin.Context) {
	var req map[string]interface{}
	c.ShouldBindJSON(&req)
	result, err := s.Orchestrator.Execute("crawl_and_ingest", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleKnowledgeExtract(c *gin.Context) {
	var req map[string]interface{}
	c.ShouldBindJSON(&req)
	result, err := s.Orchestrator.Execute("extract_entities", req, 60*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleKnowledgeQuery(c *gin.Context) {
	var req map[string]interface{}
	c.ShouldBindJSON(&req)
	result, err := s.Orchestrator.Execute("query_graph", req, 30*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleWorldKnowledgeQuery(c *gin.Context) {
	query := c.Query("query")
	limitStr := c.DefaultQuery("limit", "10")
	var limit int
	fmt.Sscanf(limitStr, "%d", &limit)

	facts, err := s.Knowledge.QueryKnowledge(query, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"facts":   facts,
		"count":   len(facts),
	})
}

func (s *Server) handleWorldKnowledgeAdd(c *gin.Context) {
	var req struct {
		Fact          string            `json:"fact"`
		Entities      []string          `json:"entities"`
		Relationships map[string]string `json:"relationships"`
		Confidence    float64           `json:"confidence"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := s.Knowledge.AddKnowledge(req.Fact, req.Entities, req.Relationships, req.Confidence)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"success": true, "id": id})
}

func (s *Server) handleCodeReview(c *gin.Context) {
	var req struct {
		Code       string `json:"code"`
		ReviewType string `json:"review_type"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.CodeReview.ReviewCode(req.Code, req.ReviewType)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodeScore(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.CodeReview.ReviewCode(req.Code, "quality")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"score": result.QualityScore, "success": true})
}

func (s *Server) handleCodeMetrics(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.CodeMetrics.CalculateMetrics(req.Code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodeComplexity(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.CodeMetrics.CalculateMetrics(req.Code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result.Complexity)
}

func (s *Server) handleCodeSecurityAnalyze(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Security.AnalyzeSecurity(req.Code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleRefactorSuggest(c *gin.Context) {
	var req struct {
		Code           string `json:"code"`
		RefactoringType string `json:"refactoring_type"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	rtype := req.RefactoringType
	if rtype == "" {
		rtype = "all"
	}

	result, err := s.Refactoring.SuggestRefactorings(req.Code, rtype)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodebaseSearch(c *gin.Context) {
	var req struct {
		Project    string `json:"project"`
		Query      string `json:"query"`
		SearchType string `json:"search_type"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	stype := req.SearchType
	if stype == "" {
		stype = "semantic"
	}

	result, err := s.Search.SearchCodebase(req.Project, req.Query, stype)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleMigratePlan(c *gin.Context) {
	var req struct {
		Code          string `json:"code"`
		TargetVersion string `json:"target_version"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	target := req.TargetVersion
	if target == "" {
		target = "3.11"
	}

	result, err := s.Migration.PlanMigration(req.Code, target)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleMigrateExecute(c *gin.Context) {
	var req struct {
		Code        string `json:"code"`
		FromVersion string `json:"from_version"`
		ToVersion   string `json:"to_version"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	from := req.FromVersion
	if from == "" {
		from = "2.7"
	}
	to := req.ToVersion
	if to == "" {
		to = "3.11"
	}

	result, err := s.Migration.MigratePythonVersion(req.Code, from, to)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleStyleDetect(c *gin.Context) {
	var req struct {
		Codebase string `json:"codebase"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Style.DetectStyle(req.Codebase)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleStyleAdapt(c *gin.Context) {
	var req struct {
		Code        string                 `json:"code"`
		TargetStyle map[string]interface{} `json:"target_style"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Style.AdaptToStyle(req.Code, req.TargetStyle)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleLearningCorrection(c *gin.Context) {
	var req struct {
		Original  string                 `json:"original"`
		Corrected string                 `json:"corrected"`
		Context   map[string]interface{} `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Learning.LearnFromCorrection(req.Original, req.Corrected, req.Context)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleLearningPersonalize(c *gin.Context) {
	var req struct {
		Preferences map[string]interface{} `json:"preferences"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Learning.PersonalizeGeneration(req.Preferences)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodeMemoryRemember(c *gin.Context) {
	var req struct {
		Pattern string                 `json:"pattern"`
		Context map[string]interface{} `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.CodeMemory.RememberCodePattern(req.Pattern, req.Context)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodeMemoryRecall(c *gin.Context) {
	var req struct {
		Code  string `json:"code"`
		Limit int    `json:"limit"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	limit := req.Limit
	if limit == 0 {
		limit = 5
	}

	result, err := s.CodeMemory.RecallSimilarPatterns(req.Code, limit)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleEmbedCode(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Embeddings.EmbedCode(req.Code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleSimilarCode(c *gin.Context) {
	var req struct {
		Code1 string `json:"code1"`
		Code2 string `json:"code2"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Embeddings.CodeSimilarity(req.Code1, req.Code2)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleProjectUnderstand(c *gin.Context) {
	var req struct {
		Project string `json:"project"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.ProjectUnder.UnderstandProject(req.Project)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleGenerateDocstring(c *gin.Context) {
	var req struct {
		Code  string `json:"code"`
		Style string `json:"style"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.DocGen.GenerateDocstring(req.Code, req.Style)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleGenerateReadme(c *gin.Context) {
	var req struct {
		Project string `json:"project"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.DocGen.GenerateReadme(req.Project)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleAnalyzeDocument(c *gin.Context) {
	var req struct {
		Text     string `json:"text"`
		FileName string `json:"file_name"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Document.AnalyzeDocument(c.Request.Context(), req.Text, req.FileName)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (s *Server) handleExplainCode(c *gin.Context) {
	var req struct {
		Code     string `json:"code"`
		Audience string `json:"audience"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.DocGen.ExplainCode(req.Code, req.Audience)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleCodeSemanticsAnalyze(c *gin.Context) {
	var req struct {
		Code string `json:"code"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.SemanticUnder.AnalyzeSemantics(req.Code)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleEmotionScore(c *gin.Context) {
	var req struct {
		Text    string `json:"text"`
		Context string `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := s.Emotion.ScoreEmotionalIntent(req.Text, req.Context)
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleEmotionWarmth(c *gin.Context) {
	var req struct {
		Score *service.EmotionalScore `json:"score"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result := s.Emotion.CalculateWarmthLevel(req.Score)
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleReasoningCode(c *gin.Context) {
	var req struct {
		Requirements string `json:"requirements"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Coordinator.GenerateCodeReasoning(req.Requirements, 120*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleReasoningFlow(c *gin.Context) {
	var req struct {
		Query   string                 `json:"query"`
		Context map[string]interface{} `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.ReasoningOrch.ExecuteReasoning(req.Query, req.Context)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleConvertThoughtGraph(c *gin.Context) {
	var req struct {
		Nodes   []interface{} `json:"mcts_nodes"`
		Context string        `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.ThoughtToText.ConvertThoughtGraph(req.Nodes, req.Context)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleConvertReasoningTree(c *gin.Context) {
	var req struct {
		Tree    map[string]interface{} `json:"tree"`
		Context string                 `json:"context"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.ThoughtToText.ConvertReasoningTree(req.Tree, req.Context)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handlePipelineRun(c *gin.Context) {
	var req struct {
		Query  string                 `json:"query"`
		Config map[string]interface{} `json:"config"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.Pipeline.ExecutePipeline(req.Query, req.Config)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

func (s *Server) handleConversationalResponse(c *gin.Context) {
	var req struct {
		Input   string `json:"input"`
		Context string `json:"context"`
		Persona string `json:"persona"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	result, err := s.ConvOrch.GenerateResponse(req.Input, req.Context, req.Persona)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, result)
}

// Ollama Aliases
func (s *Server) handleOllamaGenerate(c *gin.Context) {
	var req struct {
		Model  string `json:"model"`
		Prompt string `json:"prompt"`
		Stream bool   `json:"stream"`
	}
	c.ShouldBindJSON(&req)
	// Map to chat completions
	c.Request.Body = io.NopCloser(strings.NewReader(fmt.Sprintf(`{"model":"%s","messages":[{"role":"user","content":"%s"}],"stream":%v}`, req.Model, req.Prompt, req.Stream)))
	s.handleChatCompletions(c)
}

func (s *Server) handleOllamaChat(c *gin.Context) {
	s.handleChatCompletions(c)
}

func (s *Server) handleOllamaTags(c *gin.Context) {
	s.handleListModels(c)
}

// Placeholder CRUD handlers for Agents/Skills/Rules (would use service methods)
func (s *Server) handleCreateAgent(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Agent creation for now"}) }
func (s *Server) handleUpdateAgent(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Agent update for now"}) }
func (s *Server) handleDeleteAgent(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Agent deletion for now"}) }
func (s *Server) handleCreateSkill(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Skill creation for now"}) }
func (s *Server) handleUpdateSkill(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Skill update for now"}) }
func (s *Server) handleDeleteSkill(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Skill deletion for now"}) }
func (s *Server) handleCreateRule(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Rule creation for now"}) }
func (s *Server) handleUpdateRule(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Rule update for now"}) }
func (s *Server) handleDeleteRule(c *gin.Context) { c.JSON(http.StatusNotImplemented, gin.H{"error": "Use Python API for Rule deletion for now"}) }

// ... (previous handlers remain)

func (s *Server) handleListSkills(c *gin.Context) {
	skills := s.Skills.ListSkills()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"skills":  skills,
	})
}

func (s *Server) handleGetSkill(c *gin.Context) {
	name := c.Param("name")
	skill, ok := s.Skills.GetSkill(name)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Skill %s not found", name)})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"skill":   skill,
	})
}

func (s *Server) handleListRules(c *gin.Context) {
	rules := s.Rules.ListRules()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"rules":   rules,
	})
}

func (s *Server) handleGetRule(c *gin.Context) {
	name := c.Param("name")
	rule, ok := s.Rules.GetRule(name)
	if !ok {
		c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Rule %s not found", name)})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"rule":    rule,
	})
}

// ... (handleChatCompletions, handleSwarmRun, handleSwarmInject, handleListModels remain unchanged)

func (s *Server) handleListGoals(c *gin.Context) {
	status := c.Query("status")
	objectives, err := s.Goals.ListObjectives(status)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"goals": objectives,
		"count": len(objectives),
	})
}

func (s *Server) handleCreateGoal(c *gin.Context) {
	var req struct {
		Goal     string                 `json:"goal"`
		Priority int                    `json:"priority"`
		Metadata map[string]interface{} `json:"metadata"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	id, err := s.Goals.AddObjective(req.Goal, req.Priority, req.Metadata)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Fetch the created goal to return it
	objectives, _ := s.Goals.ListObjectives("")
	for _, obj := range objectives {
		if obj.ID == id {
			c.JSON(http.StatusOK, obj)
			return
		}
	}
	c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to retrieve created goal"})
}

func (s *Server) handleGetGoal(c *gin.Context) {
	id := c.Param("id")
	objectives, _ := s.Goals.ListObjectives("")
	var goal *service.Objective
	for _, obj := range objectives {
		if obj.ID == id {
			goal = &obj
			break
		}
	}

	if goal == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": fmt.Sprintf("Goal %s not found", id)})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"goal": goal,
		"plan_state": map[string]interface{}{}, // Placeholder for now
	})
}

func (s *Server) handleListAgents(c *gin.Context) {
	profiles := s.Profiles.ListProfiles()
	c.JSON(http.StatusOK, profiles)
}

func (s *Server) handleGetMentalState(c *gin.Context) {
	state, count := s.Subconscious.GetMentalState()
	c.JSON(http.StatusOK, gin.H{
		"mental_state": state,
		"buffer_count": count,
	})
}

func (s *Server) handleGetBudgetBalance(c *gin.Context) {
	balance := s.Budget.GetBalance()
	c.JSON(http.StatusOK, gin.H{
		"balance":  balance,
		"currency": "credits",
	})
}

func (s *Server) handleListUntrainedInsights(c *gin.Context) {
	minScoreStr := c.DefaultQuery("min_score", "0.7")
	var minScore float64
	fmt.Sscanf(minScoreStr, "%f", &minScore)

	insights, err := s.Insights.ListUntrainedInsights(minScore)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"success":  true,
		"insights": insights,
		"count":    len(insights),
	})
}

func (s *Server) handleCachePrecog(c *gin.Context) {
	var req struct {
		Query    string                 `json:"query"`
		Response map[string]interface{} `json:"response"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	s.Precog.CacheResponse(req.Query, req.Response)
	c.JSON(http.StatusOK, gin.H{"success": true})
}

func (s *Server) handleGetPrecog(c *gin.Context) {
	query := c.Query("query")
	response, found := s.Precog.GetResponse(query)
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"found": false})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"found":    true,
		"response": response,
	})
}

func (s *Server) handleGetAbsorptionCount(c *gin.Context) {
	count := s.Absorption.GetBufferCount()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"count":   count,
	})
}

func (s *Server) handleGetMetrics(c *gin.Context) {
	metrics := s.Metrics.GetAllMetrics()
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"metrics": metrics,
	})
}

func (s *Server) handleGetTraces(c *gin.Context) {
	limitStr := c.DefaultQuery("limit", "20")
	var limit int
	fmt.Sscanf(limitStr, "%d", &limit)

	traces := s.TraceStore.ListRecent(limit)
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"traces":  traces,
		"count":   len(traces),
	})
}

// handleChatCompletions handles OpenAI-compatible chat requests
func (s *Server) handleChatCompletions(c *gin.Context) {
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	log.Printf("[API] Received ChatCompletion request")

	// Extract query from last user message
	query := ""
	msgs, ok := req["messages"].([]interface{})
	if ok && len(msgs) > 0 {
		lastMsg, ok := msgs[len(msgs)-1].(map[string]interface{})
		if ok {
			query, _ = lastMsg["content"].(string)
		}
	}

	// 1. Run the Go Agent Loop
	answer, err := s.Agent.Run(query, nil)
	if err != nil {
		log.Printf("[API] Agent execution failed: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Clean up reasoning/JSON if the agent included it in the final string
	finalContent := answer
	if strings.Contains(answer, "}") {
		// If the agent returned raw JSON at the end, try to extract the thought
		var decision struct {
			Thought string `json:"thought"`
		}
		jsonStr := answer
		if strings.Contains(answer, "```json") {
			parts := strings.Split(answer, "```json")
			if len(parts) > 1 {
				jsonStr = strings.Split(parts[1], "```")[0]
			}
		}
		if err := json.Unmarshal([]byte(jsonStr), &decision); err == nil && decision.Thought != "" {
			finalContent = decision.Thought
		}
	}

	model, _ := req["model"].(string)
	if model == "" {
		model = "oricli-swarm"
	}

	openAIResp := map[string]interface{}{
		"id":      fmt.Sprintf("chatcmpl-%d", time.Now().Unix()),
		"object":  "chat.completion",
		"created": time.Now().Unix(),
		"model":   model,
		"choices": []map[string]interface{}{
			{
				"index": 0,
				"message": map[string]string{
					"role":    "assistant",
					"content": finalContent,
				},
				"finish_reason": "stop",
			},
		},
		"usage": map[string]int{
			"prompt_tokens":     0,
			"completion_tokens": 0,
			"total_tokens":      0,
		},
	}

	c.JSON(http.StatusOK, openAIResp)
}

// handleSwarmRun triggers a multi-agent swarm deliberation
func (s *Server) handleSwarmRun(c *gin.Context) {
	var req map[string]interface{}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	query, _ := req["query"].(string)
	log.Printf("[API] Triggering Swarm Run for: %s", query)

	// Route to the Hive Orchestrator
	result, err := s.Orchestrator.Execute("swarm_run", req, 300*time.Second)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, result)
}

func (s *Server) handleSwarmInject(c *gin.Context) {
	var req struct {
		Topic    string                 `json:"topic"`
		Payload  map[string]interface{} `json:"payload"`
		Protocol string                 `json:"protocol"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	s.Orchestrator.Bus.Publish(bus.Message{
		Protocol: bus.Protocol(req.Protocol),
		Topic:    req.Topic,
		SenderID: "python_bridge",
		Payload:  req.Payload,
	})

	c.JSON(http.StatusOK, gin.H{"success": true})
}

func (s *Server) handleListModels(c *gin.Context) {
	// Simple static list for now, can be dynamic later
	models := []map[string]interface{}{
		{"id": "oricli-swarm", "object": "model", "owned_by": "thynaptic"},
		{"id": "cognitive_generator", "object": "model", "owned_by": "thynaptic"},
	}
	c.JSON(http.StatusOK, gin.H{"object": "list", "data": models})
}

func (s *Server) handleDetailedHealth(c *gin.Context) {
	results, err := s.Health.ScanAllModules(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, results)
}


func (s *Server) Start() error {
	addr := fmt.Sprintf(":%d", s.Port)
	log.Printf("[API] Gateway starting on %s", addr)
	return s.Router.Run(addr)
}
