//! Safe Rust counterpart of programmable bounded TinyMemory.

/// Current TinyMemory instruction width in bytes.
pub const INSTRUCTION_BYTES: usize = 4;
/// Current self-hosting bounded RAM size.
pub const RAM_SIZE: usize = 1024;
/// TinyMemory has x0 plus seven mutable registers.
pub const NUM_REGS: usize = 8;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StuckReason {
    InvalidOpcode,
    InvalidRegister,
    MisalignedPc,
    MisalignedTarget,
    OutOfBounds,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Status {
    Running,
    Halted,
    Stuck(StuckReason),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HandlerKind {
    Addi,
    Add,
    Lb,
    Sb,
    Beq,
    Goto,
    Slli,
    Srli,
    Srai,
    Mul,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DispatchCase {
    Terminal,
    MisalignedPc,
    FetchOutOfBounds,
    InvalidOpcode,
    Halt,
    Handler(HandlerKind),
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct State {
    pub status: Status,
    pub pc: u32,
    pub regs: [u32; NUM_REGS],
    pub mem: [u8; RAM_SIZE],
}

impl Default for State {
    fn default() -> Self {
        Self {
            status: Status::Running,
            pc: 0,
            regs: [0; NUM_REGS],
            mem: [0; RAM_SIZE],
        }
    }
}

impl State {
    pub fn read_reg(&self, index: usize) -> u32 {
        if index == 0 {
            0
        } else {
            self.regs.get(index).copied().unwrap_or(0)
        }
    }

    pub fn write_reg(&mut self, index: usize, value: u32) {
        if index != 0 {
            if let Some(register) = self.regs.get_mut(index) {
                *register = value;
            }
        }
    }
}

fn instruction_bytes(state: &State) -> Option<[u8; INSTRUCTION_BYTES]> {
    let start = state.pc as usize;
    let end = start.checked_add(INSTRUCTION_BYTES)?;
    state.mem.get(start..end)?.try_into().ok()
}

#[inline(never)]
pub fn dispatch(state: &State) -> DispatchCase {
    if state.status != Status::Running {
        return DispatchCase::Terminal;
    }
    if state.pc & 3 != 0 {
        return DispatchCase::MisalignedPc;
    }
    let Some([opcode, _, _, _]) = instruction_bytes(state) else {
        return DispatchCase::FetchOutOfBounds;
    };
    match opcode {
        0 => DispatchCase::Halt,
        1 => DispatchCase::Handler(HandlerKind::Addi),
        2 => DispatchCase::Handler(HandlerKind::Add),
        3 => DispatchCase::Handler(HandlerKind::Lb),
        4 => DispatchCase::Handler(HandlerKind::Sb),
        5 => DispatchCase::Handler(HandlerKind::Beq),
        6 => DispatchCase::Handler(HandlerKind::Goto),
        7 => DispatchCase::Handler(HandlerKind::Slli),
        8 => DispatchCase::Handler(HandlerKind::Srli),
        9 => DispatchCase::Handler(HandlerKind::Srai),
        10 => DispatchCase::Handler(HandlerKind::Mul),
        _ => DispatchCase::InvalidOpcode,
    }
}

fn with_status(state: &State, status: Status) -> State {
    let mut successor = state.clone();
    successor.status = status;
    successor
}

#[inline(never)]
fn addi_handler(state: &State) -> State {
    let Some([_, rd, rs1, immediate]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let immediate = immediate as i8 as i32 as u32;
    let value = state.read_reg(rs1).wrapping_add(immediate);
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn add_handler(state: &State) -> State {
    let Some([_, rd, rs1, rs2]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    let rs2 = rs2 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS || rs2 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let value = state.read_reg(rs1).wrapping_add(state.read_reg(rs2));
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn mul_handler(state: &State) -> State {
    let Some([_, rd, rs1, rs2]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    let rs2 = rs2 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS || rs2 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let value = state.read_reg(rs1).wrapping_mul(state.read_reg(rs2));
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn slli_handler(state: &State) -> State {
    let Some([_, rd, rs1, shift]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let shift = u32::from(shift & 0x1f);
    let value = state.read_reg(rs1) << shift;
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn srli_handler(state: &State) -> State {
    let Some([_, rd, rs1, shift]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let shift = u32::from(shift & 0x1f);
    let value = state.read_reg(rs1) >> shift;
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn srai_handler(state: &State) -> State {
    let Some([_, rd, rs1, shift]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let shift = u32::from(shift & 0x1f);
    let value = ((state.read_reg(rs1) as i32) >> shift) as u32;
    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, value);
    successor
}

#[inline(never)]
fn lb_handler(state: &State) -> State {
    let Some([_, rd, rs1, immediate]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rd = rd as usize;
    let rs1 = rs1 as usize;
    if rd >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let immediate = immediate as i8 as i32 as u32;
    let address = state.read_reg(rs1).wrapping_add(immediate);
    let Some(value) = state.mem.get(address as usize).copied() else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };

    let mut successor = state.clone();
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor.write_reg(rd, u32::from(value));
    successor
}

#[inline(never)]
fn sb_handler(state: &State) -> State {
    let Some([_, rs2, rs1, immediate]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rs2 = rs2 as usize;
    let rs1 = rs1 as usize;
    if rs2 >= NUM_REGS || rs1 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    let immediate = immediate as i8 as i32 as u32;
    let address = state.read_reg(rs1).wrapping_add(immediate);
    if state.mem.get(address as usize).is_none() {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    }

    let value = state.read_reg(rs2) as u8;
    let mut successor = state.clone();
    let Some(cell) = successor.mem.get_mut(address as usize) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    *cell = value;
    successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
    successor
}

#[inline(never)]
fn beq_handler(state: &State) -> State {
    let Some([_, rs1, rs2, displacement]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let rs1 = rs1 as usize;
    let rs2 = rs2 as usize;
    if rs1 >= NUM_REGS || rs2 >= NUM_REGS {
        return with_status(state, Status::Stuck(StuckReason::InvalidRegister));
    }

    if state.read_reg(rs1) != state.read_reg(rs2) {
        let mut successor = state.clone();
        successor.pc = successor.pc.wrapping_add(INSTRUCTION_BYTES as u32);
        return successor;
    }

    let displacement = displacement as i8 as i32 as u32;
    let target = state.pc.wrapping_add(displacement);
    if target & 3 != 0 {
        return with_status(state, Status::Stuck(StuckReason::MisalignedTarget));
    }

    let mut successor = state.clone();
    successor.pc = target;
    successor
}

#[inline(never)]
fn goto_handler(state: &State) -> State {
    let Some([_, lo, mid, hi]) = instruction_bytes(state) else {
        return with_status(state, Status::Stuck(StuckReason::OutOfBounds));
    };
    let payload = u32::from(lo) | (u32::from(mid) << 8) | (u32::from(hi) << 16);
    let displacement = if payload & 0x0080_0000 == 0 {
        payload
    } else {
        payload | 0xff00_0000
    };
    let target = state.pc.wrapping_add(displacement);
    if target & 3 != 0 {
        return with_status(state, Status::Stuck(StuckReason::MisalignedTarget));
    }

    let mut successor = state.clone();
    successor.pc = target;
    successor
}

/// Execute one complete bounded TinyMemory step.
pub fn step(state: &State) -> Option<State> {
    match dispatch(state) {
        DispatchCase::Terminal => None,
        DispatchCase::MisalignedPc => {
            Some(with_status(state, Status::Stuck(StuckReason::MisalignedPc)))
        }
        DispatchCase::FetchOutOfBounds => {
            Some(with_status(state, Status::Stuck(StuckReason::OutOfBounds)))
        }
        DispatchCase::InvalidOpcode => Some(with_status(
            state,
            Status::Stuck(StuckReason::InvalidOpcode),
        )),
        DispatchCase::Halt => Some(with_status(state, Status::Halted)),
        DispatchCase::Handler(HandlerKind::Addi) => Some(addi_handler(state)),
        DispatchCase::Handler(HandlerKind::Add) => Some(add_handler(state)),
        DispatchCase::Handler(HandlerKind::Mul) => Some(mul_handler(state)),
        DispatchCase::Handler(HandlerKind::Slli) => Some(slli_handler(state)),
        DispatchCase::Handler(HandlerKind::Srli) => Some(srli_handler(state)),
        DispatchCase::Handler(HandlerKind::Srai) => Some(srai_handler(state)),
        DispatchCase::Handler(HandlerKind::Lb) => Some(lb_handler(state)),
        DispatchCase::Handler(HandlerKind::Sb) => Some(sb_handler(state)),
        DispatchCase::Handler(HandlerKind::Beq) => Some(beq_handler(state)),
        DispatchCase::Handler(HandlerKind::Goto) => Some(goto_handler(state)),
    }
}

#[cfg(test)]
mod tests {
    use super::{
        dispatch, step, DispatchCase, HandlerKind, State, Status, StuckReason, INSTRUCTION_BYTES,
        NUM_REGS, RAM_SIZE,
    };

    #[test]
    fn instruction_width_is_four_bytes() {
        assert_eq!(INSTRUCTION_BYTES, 4);
    }

    #[test]
    fn x0_is_immutable() {
        let mut state = State::default();
        state.regs[0] = 17;
        assert_eq!(state.read_reg(0), 0);
        state.write_reg(0, u32::MAX);
        assert_eq!(state.regs[0], 17);
        assert_eq!(state.read_reg(0), 0);
    }

    #[test]
    fn predispatch_priority_and_routes() {
        let mut state = State {
            status: Status::Halted,
            pc: 1,
            ..State::default()
        };
        assert_eq!(dispatch(&state), DispatchCase::Terminal);

        state.status = Status::Running;
        assert_eq!(dispatch(&state), DispatchCase::MisalignedPc);

        state.pc = RAM_SIZE as u32;
        assert_eq!(dispatch(&state), DispatchCase::FetchOutOfBounds);

        state.pc = 0;
        state.mem[0] = u8::MAX;
        assert_eq!(dispatch(&state), DispatchCase::InvalidOpcode);

        state.mem[0] = 0;
        assert_eq!(dispatch(&state), DispatchCase::Halt);

        let handlers = [
            HandlerKind::Addi,
            HandlerKind::Add,
            HandlerKind::Lb,
            HandlerKind::Sb,
            HandlerKind::Beq,
            HandlerKind::Goto,
            HandlerKind::Slli,
            HandlerKind::Srli,
            HandlerKind::Srai,
            HandlerKind::Mul,
        ];
        for (opcode, handler) in (1u8..=10).zip(handlers) {
            state.mem[0] = opcode;
            assert_eq!(dispatch(&state), DispatchCase::Handler(handler));
        }

        state.status = Status::Stuck(StuckReason::OutOfBounds);
        assert_eq!(dispatch(&state), DispatchCase::Terminal);
    }

    #[test]
    fn addi_sign_extends_and_wraps() {
        let mut state = State::default();
        state.regs[2] = 1;
        state.mem[..4].copy_from_slice(&[1, 3, 2, 0xfe]);

        let Some(successor) = step(&state) else {
            panic!("ADDI must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[3], u32::MAX);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn addi_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.mem[..4].copy_from_slice(&[1, 0, 0, 7]);

        let Some(successor) = step(&state) else {
            panic!("ADDI must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn addi_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[1, NUM_REGS as u8, 1, 4]);

        let Some(successor) = step(&state) else {
            panic!("invalid ADDI must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn add_wraps_and_advances_pc() {
        let mut state = State::default();
        state.regs[2] = u32::MAX;
        state.regs[3] = 2;
        state.mem[..4].copy_from_slice(&[2, 1, 2, 3]);

        let Some(successor) = step(&state) else {
            panic!("ADD must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 1);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn add_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.regs[1] = 12;
        state.mem[..4].copy_from_slice(&[2, 0, 0, 1]);

        let Some(successor) = step(&state) else {
            panic!("ADD must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn add_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[2, 1, 1, NUM_REGS as u8]);

        let Some(successor) = step(&state) else {
            panic!("invalid ADD must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn mul_wraps_and_advances_pc() {
        let mut state = State::default();
        state.regs[2] = 0x8000_0001;
        state.regs[3] = 2;
        state.mem[..4].copy_from_slice(&[10, 1, 2, 3]);

        let Some(successor) = step(&state) else {
            panic!("MUL must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 2);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn mul_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.regs[1] = 12;
        state.mem[..4].copy_from_slice(&[10, 0, 0, 1]);

        let Some(successor) = step(&state) else {
            panic!("MUL must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn mul_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[10, 1, NUM_REGS as u8, 1]);

        let Some(successor) = step(&state) else {
            panic!("invalid MUL must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn slli_masks_shift_to_low_five_bits() {
        let mut state = State::default();
        state.regs[2] = 3;
        state.mem[..4].copy_from_slice(&[7, 1, 2, 33]);

        let Some(successor) = step(&state) else {
            panic!("SLLI must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 6);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn slli_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.mem[..4].copy_from_slice(&[7, 0, 0, 7]);

        let Some(successor) = step(&state) else {
            panic!("SLLI must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn slli_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[7, 1, NUM_REGS as u8, 4]);

        let Some(successor) = step(&state) else {
            panic!("invalid SLLI must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn srli_masks_shift_to_low_five_bits() {
        let mut state = State::default();
        state.regs[2] = 0x8000_0002;
        state.mem[..4].copy_from_slice(&[8, 1, 2, 33]);

        let Some(successor) = step(&state) else {
            panic!("SRLI must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 0x4000_0001);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn srli_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.mem[..4].copy_from_slice(&[8, 0, 0, 7]);

        let Some(successor) = step(&state) else {
            panic!("SRLI must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn srli_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[8, NUM_REGS as u8, 1, 4]);

        let Some(successor) = step(&state) else {
            panic!("invalid SRLI must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn srai_masks_shift_and_propagates_sign() {
        let mut state = State::default();
        state.regs[2] = 0x8000_0002;
        state.mem[..4].copy_from_slice(&[9, 1, 2, 33]);

        let Some(successor) = step(&state) else {
            panic!("SRAI must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 0xc000_0001);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn srai_observes_x0_read_and_write_rules() {
        let mut state = State::default();
        state.regs[0] = 99;
        state.mem[..4].copy_from_slice(&[9, 0, 0, 7]);

        let Some(successor) = step(&state) else {
            panic!("SRAI must step");
        };
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[0], 99);
        assert_eq!(successor.read_reg(0), 0);
    }

    #[test]
    fn srai_invalid_register_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.mem[..4].copy_from_slice(&[9, 1, NUM_REGS as u8, 4]);

        let Some(successor) = step(&state) else {
            panic!("invalid SRAI must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn lb_uses_signed_offset_and_zero_extends_byte() {
        let mut state = State::default();
        state.regs[2] = 5;
        state.mem[4] = 0xfe;
        state.mem[..4].copy_from_slice(&[3, 1, 2, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("LB must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs[1], 0xfe);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn lb_out_of_bounds_preserves_architectural_state() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[3, 1, 0, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("out-of-bounds LB must produce a stuck successor");
        };
        assert_eq!(successor.status, Status::Stuck(StuckReason::OutOfBounds));
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn lb_invalid_register_precedes_address_check() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[3, NUM_REGS as u8, 0, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("invalid LB must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn sb_uses_signed_offset_and_stores_low_byte() {
        let mut state = State::default();
        state.regs[1] = 0x1234_56fe;
        state.regs[2] = 5;
        state.mem[..4].copy_from_slice(&[4, 1, 2, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("SB must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.mem[4], 0xfe);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(&successor.mem[5..], &state.mem[5..]);
    }

    #[test]
    fn sb_out_of_bounds_preserves_architectural_state() {
        let mut state = State::default();
        state.regs[1] = 0xaa;
        state.mem[..4].copy_from_slice(&[4, 1, 0, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("out-of-bounds SB must produce a stuck successor");
        };
        assert_eq!(successor.status, Status::Stuck(StuckReason::OutOfBounds));
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn sb_invalid_register_precedes_address_check() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[4, NUM_REGS as u8, 0, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("invalid SB must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn beq_taken_uses_signed_aligned_target() {
        let mut state = State::default();
        state.pc = 4;
        state.regs[1] = 23;
        state.regs[2] = 23;
        state.mem[4..8].copy_from_slice(&[5, 1, 2, 0xfc]);

        let Some(successor) = step(&state) else {
            panic!("BEQ must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 0);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn beq_taken_misaligned_target_preserves_state() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.regs[2] = 23;
        state.mem[..4].copy_from_slice(&[5, 1, 2, 2]);

        let Some(successor) = step(&state) else {
            panic!("misaligned BEQ must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::MisalignedTarget)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn beq_not_taken_ignores_target_alignment() {
        let mut state = State::default();
        state.regs[1] = 23;
        state.regs[2] = 24;
        state.mem[..4].copy_from_slice(&[5, 1, 2, 2]);

        let Some(successor) = step(&state) else {
            panic!("BEQ must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 4);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn beq_invalid_register_precedes_branch_checks() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[5, NUM_REGS as u8, 0, 2]);

        let Some(successor) = step(&state) else {
            panic!("invalid BEQ must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::InvalidRegister)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn goto_sign_extends_24_bit_displacement() {
        let mut state = State::default();
        state.pc = 4;
        state.mem[4..8].copy_from_slice(&[6, 0xfc, 0xff, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("GOTO must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 0);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn goto_misaligned_target_preserves_state() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[6, 2, 0, 0]);

        let Some(successor) = step(&state) else {
            panic!("misaligned GOTO must produce a stuck successor");
        };
        assert_eq!(
            successor.status,
            Status::Stuck(StuckReason::MisalignedTarget)
        );
        assert_eq!(successor.pc, state.pc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }

    #[test]
    fn goto_allows_aligned_target_outside_ram() {
        let mut state = State::default();
        state.mem[..4].copy_from_slice(&[6, 0xfc, 0xff, 0xff]);

        let Some(successor) = step(&state) else {
            panic!("GOTO must step");
        };
        assert_eq!(successor.status, Status::Running);
        assert_eq!(successor.pc, 0xffff_fffc);
        assert_eq!(successor.regs, state.regs);
        assert_eq!(successor.mem, state.mem);
    }
}
