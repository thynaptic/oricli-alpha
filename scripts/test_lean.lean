def add_positive (a b : Nat) : Nat :=
if h : a > 0 ∧ b > 0 then
  a + b
else
  0
