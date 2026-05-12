package cognition

import (
	"sort"
	"strconv"
	"strings"
)

type SemanticMemoryGraphRequest struct {
	Surface       string                   `json:"surface,omitempty"`
	Objective     string                   `json:"objective,omitempty"`
	Workspace     string                   `json:"workspace,omitempty"`
	Query         string                   `json:"query,omitempty"`
	Captures      []SemanticMemoryCapture  `json:"captures,omitempty"`
	ExistingNodes []SemanticMemoryNodeSeed `json:"existing_nodes,omitempty"`
	Constraints   []string                 `json:"constraints,omitempty"`
	Metadata      map[string]interface{}   `json:"metadata,omitempty"`
}

type SemanticMemoryCapture struct {
	ID      string   `json:"id,omitempty"`
	Title   string   `json:"title,omitempty"`
	Content string   `json:"content,omitempty"`
	Source  string   `json:"source,omitempty"`
	Kind    string   `json:"kind,omitempty"`
	Time    string   `json:"time,omitempty"`
	Tags    []string `json:"tags,omitempty"`
	People  []string `json:"people,omitempty"`
	Objects []string `json:"objects,omitempty"`
}

type SemanticMemoryNodeSeed struct {
	ID     string   `json:"id,omitempty"`
	Label  string   `json:"label,omitempty"`
	Kind   string   `json:"kind,omitempty"`
	Source string   `json:"source,omitempty"`
	Tags   []string `json:"tags,omitempty"`
}

type SemanticMemoryGraph struct {
	ID                   string                         `json:"id"`
	Surface              string                         `json:"surface"`
	Workspace            string                         `json:"workspace,omitempty"`
	Objective            string                         `json:"objective"`
	Summary              string                         `json:"summary"`
	Nodes                []SemanticMemoryNode           `json:"nodes,omitempty"`
	Edges                []SemanticMemoryEdge           `json:"edges,omitempty"`
	Clusters             []SemanticMemoryCluster        `json:"clusters,omitempty"`
	Recoverability       SemanticRecoverabilityIndex    `json:"recoverability"`
	RetrievalPlan        []SemanticRetrievalMove        `json:"retrieval_plan,omitempty"`
	ProgressiveStructure SemanticProgressiveStructure   `json:"progressive_structure"`
	MemorySeeds          []QuestMemorySeed              `json:"memory_seeds,omitempty"`
	Integration          SemanticMemoryGraphIntegration `json:"integration"`
	Guardrails           []string                       `json:"guardrails"`
	OpenQuestions        []string                       `json:"open_questions,omitempty"`
}

type SemanticMemoryNode struct {
	ID         string   `json:"id"`
	Label      string   `json:"label"`
	Kind       string   `json:"kind"`
	SourceIDs  []string `json:"source_ids,omitempty"`
	Tags       []string `json:"tags,omitempty"`
	Aliases    []string `json:"aliases,omitempty"`
	Confidence float64  `json:"confidence"`
}

type SemanticMemoryEdge struct {
	ID         string  `json:"id"`
	From       string  `json:"from"`
	To         string  `json:"to"`
	Relation   string  `json:"relation"`
	Why        string  `json:"why"`
	Confidence float64 `json:"confidence"`
}

type SemanticMemoryCluster struct {
	ID       string   `json:"id"`
	Label    string   `json:"label"`
	NodeIDs  []string `json:"node_ids,omitempty"`
	Why      string   `json:"why"`
	NextUse  string   `json:"next_use"`
	Strength float64  `json:"strength"`
}

type SemanticRecoverabilityIndex struct {
	Score       float64  `json:"score"`
	Level       string   `json:"level"`
	Reasons     []string `json:"reasons,omitempty"`
	Missing     []string `json:"missing,omitempty"`
	BestHandles []string `json:"best_handles,omitempty"`
}

type SemanticRetrievalMove struct {
	Query      string   `json:"query"`
	Use        string   `json:"use"`
	Handles    []string `json:"handles,omitempty"`
	StopWhen   string   `json:"stop_when"`
	Confidence float64  `json:"confidence"`
}

type SemanticProgressiveStructure struct {
	CurrentMode string   `json:"current_mode"`
	DoNow       []string `json:"do_now"`
	PromoteWhen string   `json:"promote_when"`
	DoNotForce  []string `json:"do_not_force"`
}

type SemanticMemoryGraphIntegration struct {
	Memory     []string `json:"memory"`
	WorkGraph  []string `json:"workgraph"`
	Continuity []string `json:"continuity"`
	Intent     []string `json:"intent"`
	Procedure  []string `json:"procedure"`
	Surface    []string `json:"surface"`
}

// BuildSemanticMemoryGraph turns loose captures into an ontology-free memory
// topology. The goal is recoverability without forcing users to maintain
// folders, taxonomies, or perfect upfront structure.
func BuildSemanticMemoryGraph(req SemanticMemoryGraphRequest) SemanticMemoryGraph {
	req = normalizeSemanticMemoryGraphRequest(req)
	nodes := buildSemanticMemoryNodes(req)
	edges := buildSemanticMemoryEdges(nodes, req)
	clusters := buildSemanticMemoryClusters(nodes, req)
	recoverability := scoreSemanticRecoverability(nodes, edges, clusters, req)

	return SemanticMemoryGraph{
		ID:                   "sem_mem_" + stableBehaviorID(req.Workspace+"_"+req.Objective),
		Surface:              normalizeQuestSurface(req.Surface),
		Workspace:            req.Workspace,
		Objective:            req.Objective,
		Summary:              summarizeSemanticMemoryGraph(req, nodes, edges, clusters),
		Nodes:                nodes,
		Edges:                edges,
		Clusters:             clusters,
		Recoverability:       recoverability,
		RetrievalPlan:        buildSemanticRetrievalPlan(req, clusters, recoverability),
		ProgressiveStructure: buildSemanticProgressiveStructure(req, recoverability),
		MemorySeeds:          semanticMemorySeeds(req, recoverability),
		Integration: SemanticMemoryGraphIntegration{
			Memory:     []string{"Persist nodes and edges only after source-backed confirmation or client-owned memory writes."},
			WorkGraph:  []string{"Send operational tasks, owners, deadlines, and blockers to /workgraph/compile instead of overloading memory topology."},
			Continuity: []string{"Feed high-strength clusters into /continuity/recover when they explain a returning work thread."},
			Intent:     []string{"Attach rationale-bearing captures to /intent/timeline when they explain why meaning changed."},
			Procedure:  []string{"Route repeated capture/linking behavior to /procedural/crystallize before creating workflow skills."},
			Surface:    continuitySurfaceHints(req.Surface),
		},
		Guardrails: []string{
			"Do not claim memory, documents, tags, or graph records were saved unless a tool confirms it.",
			"Prefer recoverability over premature taxonomy; suggested structure can stay soft.",
			"Keep private captures under the client surface's consent, retention, and deletion policy.",
		},
		OpenQuestions: semanticMemoryOpenQuestions(req, recoverability),
	}
}

func normalizeSemanticMemoryGraphRequest(req SemanticMemoryGraphRequest) SemanticMemoryGraphRequest {
	req.Surface = normalizeQuestSurface(req.Surface)
	req.Objective = cleanPlanningText(firstNonEmpty(req.Objective, req.Query, "make loose information recoverable"))
	req.Workspace = cleanPlanningText(firstNonEmpty(req.Workspace, "active memory"))
	req.Query = cleanPlanningText(req.Query)
	req.Constraints = uniqueActionStrings(req.Constraints)
	for i := range req.Captures {
		req.Captures[i].ID = cleanPlanningText(req.Captures[i].ID)
		req.Captures[i].Title = cleanPlanningText(req.Captures[i].Title)
		req.Captures[i].Content = cleanPlanningText(req.Captures[i].Content)
		req.Captures[i].Source = cleanPlanningText(req.Captures[i].Source)
		req.Captures[i].Kind = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.Captures[i].Kind, "capture")))
		req.Captures[i].Time = cleanPlanningText(req.Captures[i].Time)
		req.Captures[i].Tags = uniqueActionStrings(req.Captures[i].Tags)
		req.Captures[i].People = uniqueActionStrings(req.Captures[i].People)
		req.Captures[i].Objects = uniqueActionStrings(req.Captures[i].Objects)
	}
	for i := range req.ExistingNodes {
		req.ExistingNodes[i].ID = cleanPlanningText(req.ExistingNodes[i].ID)
		req.ExistingNodes[i].Label = cleanPlanningText(req.ExistingNodes[i].Label)
		req.ExistingNodes[i].Kind = strings.ToLower(strings.TrimSpace(firstNonEmpty(req.ExistingNodes[i].Kind, "concept")))
		req.ExistingNodes[i].Source = cleanPlanningText(req.ExistingNodes[i].Source)
		req.ExistingNodes[i].Tags = uniqueActionStrings(req.ExistingNodes[i].Tags)
	}
	return req
}

func buildSemanticMemoryNodes(req SemanticMemoryGraphRequest) []SemanticMemoryNode {
	nodesByKey := map[string]SemanticMemoryNode{}
	add := func(label, kind, source string, tags []string, conf float64) {
		label = cleanPlanningText(label)
		if label == "" {
			return
		}
		kind = strings.ToLower(strings.TrimSpace(firstNonEmpty(kind, "concept")))
		key := kind + ":" + strings.ToLower(label)
		node := nodesByKey[key]
		if node.ID == "" {
			node = SemanticMemoryNode{
				ID:         "smn_" + stableBehaviorID(kind+"_"+label),
				Label:      sentenceCase(label),
				Kind:       kind,
				Confidence: conf,
			}
		}
		if source != "" {
			node.SourceIDs = appendUniquePreserve(node.SourceIDs, source)
		}
		node.Tags = uniqueActionStrings(append(node.Tags, tags...))
		if conf > node.Confidence {
			node.Confidence = conf
		}
		nodesByKey[key] = node
	}

	for _, seed := range req.ExistingNodes {
		add(seed.Label, seed.Kind, seed.Source, seed.Tags, 0.72)
	}
	for _, capture := range req.Captures {
		sourceID := firstNonEmpty(capture.ID, capture.Source, capture.Title)
		add(firstNonEmpty(capture.Title, capture.Content, "untitled capture"), capture.Kind, sourceID, capture.Tags, 0.62)
		for _, tag := range capture.Tags {
			add(tag, "topic", sourceID, nil, 0.58)
		}
		for _, person := range capture.People {
			add(person, "person", sourceID, nil, 0.64)
		}
		for _, object := range capture.Objects {
			add(object, "object", sourceID, capture.Tags, 0.6)
		}
		for _, phrase := range semanticKeyPhrases(capture.Content) {
			add(phrase, "concept", sourceID, capture.Tags, 0.46)
		}
	}
	if len(nodesByKey) == 0 {
		add("Clarify what should be recoverable", "clarification", "request", nil, 0.32)
	}

	nodes := make([]SemanticMemoryNode, 0, len(nodesByKey))
	for _, node := range nodesByKey {
		if len(node.SourceIDs) > 4 {
			node.SourceIDs = node.SourceIDs[:4]
		}
		nodes = append(nodes, node)
	}
	sort.SliceStable(nodes, func(i, j int) bool {
		if nodes[i].Confidence == nodes[j].Confidence {
			return nodes[i].Label < nodes[j].Label
		}
		return nodes[i].Confidence > nodes[j].Confidence
	})
	if len(nodes) > 12 {
		return nodes[:12]
	}
	return nodes
}

func buildSemanticMemoryEdges(nodes []SemanticMemoryNode, req SemanticMemoryGraphRequest) []SemanticMemoryEdge {
	var edges []SemanticMemoryEdge
	for _, capture := range req.Captures {
		captureNode := findSemanticNode(nodes, firstNonEmpty(capture.Title, capture.Content), capture.Kind)
		if captureNode.ID == "" {
			continue
		}
		handles := append([]string{}, capture.Tags...)
		handles = append(handles, capture.People...)
		handles = append(handles, capture.Objects...)
		for _, handle := range handles {
			target := findSemanticNodeAnyKind(nodes, handle)
			if target.ID == "" || target.ID == captureNode.ID {
				continue
			}
			relation := "mentions"
			if target.Kind == "topic" {
				relation = "tagged_with"
			}
			if target.Kind == "person" {
				relation = "involves"
			}
			edges = append(edges, SemanticMemoryEdge{
				ID:         "sme_" + stableBehaviorID(captureNode.ID+"_"+target.ID+"_"+relation),
				From:       captureNode.ID,
				To:         target.ID,
				Relation:   relation,
				Why:        "Capture metadata creates a recoverable handle.",
				Confidence: 0.66,
			})
		}
	}
	for i := 0; i < len(nodes)-1 && len(edges) < 10; i++ {
		if sharesSemanticTag(nodes[i], nodes[i+1]) {
			edges = append(edges, SemanticMemoryEdge{
				ID:         "sme_" + stableBehaviorID(nodes[i].ID+"_"+nodes[i+1].ID+"_related"),
				From:       nodes[i].ID,
				To:         nodes[i+1].ID,
				Relation:   "related_context",
				Why:        "Nodes share soft tags or source handles.",
				Confidence: 0.52,
			})
		}
	}
	return dedupeSemanticEdges(edges)
}

func buildSemanticMemoryClusters(nodes []SemanticMemoryNode, req SemanticMemoryGraphRequest) []SemanticMemoryCluster {
	groups := map[string][]string{}
	for _, node := range nodes {
		label := "general"
		if len(node.Tags) > 0 {
			label = strings.ToLower(node.Tags[0])
		} else if node.Kind != "" {
			label = node.Kind
		}
		groups[label] = append(groups[label], node.ID)
	}
	var clusters []SemanticMemoryCluster
	for label, ids := range groups {
		if len(ids) == 0 {
			continue
		}
		strength := 0.4 + float64(len(ids))*0.08
		if strength > 0.84 {
			strength = 0.84
		}
		clusters = append(clusters, SemanticMemoryCluster{
			ID:       "smc_" + stableBehaviorID(label),
			Label:    sentenceCase(label),
			NodeIDs:  ids,
			Why:      "Cluster gives loose captures a recoverable handle without requiring a folder.",
			NextUse:  "Use as a retrieval handle before asking the user to organize anything.",
			Strength: strength,
		})
	}
	sort.SliceStable(clusters, func(i, j int) bool { return clusters[i].Strength > clusters[j].Strength })
	if len(clusters) > 6 {
		return clusters[:6]
	}
	return clusters
}

func scoreSemanticRecoverability(nodes []SemanticMemoryNode, edges []SemanticMemoryEdge, clusters []SemanticMemoryCluster, req SemanticMemoryGraphRequest) SemanticRecoverabilityIndex {
	score := 0.28 + float64(len(nodes))*0.025 + float64(len(edges))*0.02 + float64(len(clusters))*0.04
	var reasons []string
	var missing []string
	var handles []string
	if len(req.Captures) > 0 {
		reasons = append(reasons, "captures supplied")
	}
	if len(edges) > 0 {
		reasons = append(reasons, "relationship handles available")
	}
	if len(clusters) > 0 {
		reasons = append(reasons, "soft clusters available")
		for _, cluster := range clusters {
			handles = append(handles, cluster.Label)
		}
	}
	if len(req.Captures) == 0 {
		missing = append(missing, "source captures")
	}
	if len(edges) == 0 {
		missing = append(missing, "semantic relationships")
	}
	if len(req.Query) == 0 {
		missing = append(missing, "retrieval question")
	}
	if score > 0.9 {
		score = 0.9
	}
	return SemanticRecoverabilityIndex{Score: score, Level: semanticRecoverabilityLevel(score), Reasons: reasons, Missing: missing, BestHandles: handles}
}

func buildSemanticRetrievalPlan(req SemanticMemoryGraphRequest, clusters []SemanticMemoryCluster, idx SemanticRecoverabilityIndex) []SemanticRetrievalMove {
	query := firstNonEmpty(req.Query, req.Objective, "recover relevant context")
	var moves []SemanticRetrievalMove
	for _, cluster := range clusters {
		moves = append(moves, SemanticRetrievalMove{
			Query:      query,
			Use:        "Search cluster: " + cluster.Label,
			Handles:    []string{cluster.Label},
			StopWhen:   "Enough source-backed context is found to answer or continue.",
			Confidence: cluster.Strength,
		})
		if len(moves) == 4 {
			break
		}
	}
	if len(moves) == 0 {
		moves = append(moves, SemanticRetrievalMove{Query: query, Use: "Ask for one source capture or remembered handle.", StopWhen: "A source or handle is supplied.", Confidence: idx.Score})
	}
	return moves
}

func buildSemanticProgressiveStructure(req SemanticMemoryGraphRequest, idx SemanticRecoverabilityIndex) SemanticProgressiveStructure {
	mode := "capture_first"
	if idx.Score >= 0.68 {
		mode = "soft_graph"
	} else if idx.Score >= 0.48 {
		mode = "cluster_first"
	}
	return SemanticProgressiveStructure{
		CurrentMode: mode,
		DoNow:       []string{"Keep captures loose.", "Attach source-backed handles.", "Prefer searchability over folder design."},
		PromoteWhen: "A cluster is repeatedly retrieved, edited, or used to make decisions.",
		DoNotForce:  []string{"Rigid folders", "premature ontology", "manual taxonomy upkeep"},
	}
}

func summarizeSemanticMemoryGraph(req SemanticMemoryGraphRequest, nodes []SemanticMemoryNode, edges []SemanticMemoryEdge, clusters []SemanticMemoryCluster) string {
	return sentenceCase(req.Objective) + " produced " + intToSemanticCount(len(nodes)) + " memory nodes, " + intToSemanticCount(len(edges)) + " edges, and " + intToSemanticCount(len(clusters)) + " soft clusters."
}

func semanticMemorySeeds(req SemanticMemoryGraphRequest, idx SemanticRecoverabilityIndex) []QuestMemorySeed {
	return []QuestMemorySeed{
		{Key: "semantic_memory_workspace", Value: req.Workspace, Importance: 0.58},
		{Key: "semantic_memory_objective", Value: req.Objective, Importance: 0.62},
		{Key: "semantic_memory_recoverability", Value: idx.Level, Importance: 0.56},
	}
}

func semanticKeyPhrases(content string) []string {
	parts := splitPlanningAtoms(content)
	var out []string
	for _, part := range parts {
		words := strings.Fields(part)
		if len(words) < 2 {
			continue
		}
		if len(words) > 5 {
			words = words[:5]
		}
		out = append(out, strings.Join(words, " "))
		if len(out) == 3 {
			break
		}
	}
	return out
}

func findSemanticNode(nodes []SemanticMemoryNode, label, kind string) SemanticMemoryNode {
	kind = strings.ToLower(strings.TrimSpace(kind))
	for _, node := range nodes {
		if strings.EqualFold(node.Label, label) && (kind == "" || node.Kind == kind) {
			return node
		}
	}
	return SemanticMemoryNode{}
}

func findSemanticNodeAnyKind(nodes []SemanticMemoryNode, label string) SemanticMemoryNode {
	for _, node := range nodes {
		if strings.EqualFold(node.Label, label) {
			return node
		}
	}
	return SemanticMemoryNode{}
}

func sharesSemanticTag(a, b SemanticMemoryNode) bool {
	for _, at := range a.Tags {
		for _, bt := range b.Tags {
			if strings.EqualFold(at, bt) {
				return true
			}
		}
	}
	for _, as := range a.SourceIDs {
		for _, bs := range b.SourceIDs {
			if strings.EqualFold(as, bs) {
				return true
			}
		}
	}
	return false
}

func dedupeSemanticEdges(edges []SemanticMemoryEdge) []SemanticMemoryEdge {
	seen := map[string]bool{}
	var out []SemanticMemoryEdge
	for _, edge := range edges {
		key := edge.From + ":" + edge.To + ":" + edge.Relation
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, edge)
	}
	if len(out) > 12 {
		return out[:12]
	}
	return out
}

func appendUniquePreserve(values []string, next string) []string {
	next = cleanPlanningText(next)
	if next == "" {
		return values
	}
	for _, value := range values {
		if strings.EqualFold(value, next) {
			return values
		}
	}
	return append(values, next)
}

func semanticRecoverabilityLevel(score float64) string {
	switch {
	case score >= 0.72:
		return "strong"
	case score >= 0.5:
		return "workable"
	default:
		return "thin"
	}
}

func semanticMemoryOpenQuestions(req SemanticMemoryGraphRequest, idx SemanticRecoverabilityIndex) []string {
	var qs []string
	if len(req.Captures) == 0 {
		qs = append(qs, "What loose capture should anchor this graph?")
	}
	if len(idx.Missing) > 0 {
		qs = append(qs, "Which missing handle would make this easier to recover later?")
	}
	if len(req.Query) == 0 {
		qs = append(qs, "What question should this memory graph help answer?")
	}
	return qs
}

func intToSemanticCount(n int) string {
	return strconv.Itoa(n)
}
