package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/cognition"
)

func (s *ServerV2) handleConversationHarvest(c *gin.Context) {
	var req cognition.ConversationHarvestRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Surface == "" {
		req.Surface = c.GetHeader("X-Ori-Context")
	}
	c.JSON(http.StatusOK, cognition.HarvestConversationContext(req))
}
