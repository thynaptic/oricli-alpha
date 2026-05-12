package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/thynaptic/oricli-go/pkg/cognition"
)

func (s *ServerV2) handleBehaviorCreate(c *gin.Context) {
	var req cognition.BehaviorReinforcementRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Surface == "" {
		req.Surface = c.GetHeader("X-Ori-Context")
	}
	c.JSON(http.StatusOK, cognition.BuildBehaviorObject(req))
}

func (s *ServerV2) handleBehaviorEvent(c *gin.Context) {
	var req cognition.BehaviorEventRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Behavior.Surface == "" {
		req.Behavior.Surface = c.GetHeader("X-Ori-Context")
	}
	c.JSON(http.StatusOK, cognition.ApplyBehaviorEvent(req))
}

func (s *ServerV2) handleBehaviorState(c *gin.Context) {
	var req cognition.BehaviorStateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	if req.Behavior.Surface == "" {
		req.Behavior.Surface = c.GetHeader("X-Ori-Context")
	}
	c.JSON(http.StatusOK, cognition.BuildBehaviorState(req))
}
