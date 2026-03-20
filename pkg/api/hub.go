package api

import (
	"encoding/json"
	"log"
	"sync"

	"github.com/gorilla/websocket"
)

// --- Pillar 48: WebSocket Hub ---
// Manages real-time state broadcasting to connected UI clients.

type WSEvent struct {
	Type    string          `json:"type"`
	Payload json.RawMessage `json:"payload"`
}

type Client struct {
	hub  *Hub
	conn *websocket.Conn
	send chan []byte
}

type Hub struct {
	clients    map[*Client]bool
	broadcast  chan []byte
	register   chan *Client
	unregister chan *Client
	mu         sync.Mutex
}

func NewHub() *Hub {
	return &Hub{
		broadcast:  make(chan []byte),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		clients:    make(map[*Client]bool),
	}
}

func (h *Hub) Run() {
	log.Println("[WebSocket] Hub is active and listening for events.")
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client] = true
			h.mu.Unlock()
			log.Println("[WebSocket] UI Client connected.")

		case client := <-h.unregister:
			h.mu.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
			h.mu.Unlock()
			log.Println("[WebSocket] UI Client disconnected.")

		case message := <-h.broadcast:
			h.mu.Lock()
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					close(client.send)
					delete(h.clients, client)
				}
			}
			h.mu.Unlock()
		}
	}
}

// BroadcastEvent marshals and sends an event to all connected clients.
func (h *Hub) BroadcastEvent(eventType string, payload interface{}) {
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		log.Printf("[WebSocket] Error marshaling event payload: %v", err)
		return
	}

	event := WSEvent{
		Type:    eventType,
		Payload: payloadBytes,
	}

	eventBytes, err := json.Marshal(event)
	if err != nil {
		log.Printf("[WebSocket] Error marshaling event: %v", err)
		return
	}

	h.broadcast <- eventBytes
}
