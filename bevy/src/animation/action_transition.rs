//! Decoded ordinary action tables; VM request predicates remain external.
use serde::Deserialize;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
pub struct Rule {
    pub requested: i32,
    pub target: u16,
    pub flags: u8,
    pub duration_byte: u8,
}
#[derive(Deserialize)]
pub struct Table {
    pub phase: u8,
    pub rows: Vec<Rule>,
}
pub fn lookup(tables: &[Table], phase: u8, requested: i32) -> Option<Rule> {
    tables
        .iter()
        .find(|t| t.phase == phase)?
        .rows
        .iter()
        .find(|r| r.requested == requested)
        .copied()
}

#[cfg(test)]
#[path = "../../tests/unit/animation/action_transition.rs"]
mod tests;
