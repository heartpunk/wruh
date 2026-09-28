//! Link anchor for the exact Linux extractor artifact.

use std::hint::black_box;

use tinymemory::{dispatch, step, State};

fn main() {
    let state = black_box(State::default());
    black_box(dispatch(&state));
    black_box(step(&state));
}
