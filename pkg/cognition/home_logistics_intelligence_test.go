package cognition

import (
	"testing"
	"time"
)

func TestBuildHomeLogisticsPlanStagesActivePin(t *testing.T) {
	now := time.Date(2026, 5, 8, 12, 0, 0, 0, time.UTC)
	plan := BuildHomeLogisticsPlan(HomeLogisticsRequest{
		Now:         now,
		Source:      "Permission slip due Monday. Pay field trip fee tomorrow. Bring red shirt for spirit day next week.",
		Preferences: HomeLogisticsPreferences{MaxPins: 3, LowNoiseMode: true},
	})
	if len(plan.Pins) != 3 {
		t.Fatalf("expected three pins, got %d", len(plan.Pins))
	}
	if plan.ActivePin == nil {
		t.Fatal("expected active pin")
	}
	if plan.ActivePin.Kind != "payment" {
		t.Fatalf("expected payment pin first due tomorrow, got %#v", plan.ActivePin)
	}
	if plan.Load.Tier == "low" {
		t.Fatalf("expected non-low household load, got %#v", plan.Load)
	}
}

func TestExtractActivePinsClassifiesResolutionKinds(t *testing.T) {
	now := time.Date(2026, 5, 8, 12, 0, 0, 0, time.UTC)
	pins := ExtractActivePins("Email teacher about pickup. Schedule parent conference Friday. Pack snack.", now)
	if len(pins) != 3 {
		t.Fatalf("expected three pins, got %d", len(pins))
	}
	kinds := map[string]bool{}
	for _, pin := range pins {
		kinds[pin.Kind] = true
	}
	for _, kind := range []string{"message", "booking", "prep"} {
		if !kinds[kind] {
			t.Fatalf("missing kind %q in %#v", kind, pins)
		}
	}
}

func TestSelectActivePinRespectsLowNoise(t *testing.T) {
	now := time.Date(2026, 5, 8, 12, 0, 0, 0, time.UTC)
	pin := SelectActivePin([]ActivePin{{Title: "Later", Urgency: "low"}, {Title: "Soon", Urgency: "medium"}}, now, HomeLogisticsPreferences{LowNoiseMode: true})
	if pin.Title != "Soon" {
		t.Fatalf("expected medium pin in low-noise mode, got %#v", pin)
	}
}
