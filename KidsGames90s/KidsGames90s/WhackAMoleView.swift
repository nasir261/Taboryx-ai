import SwiftUI

struct WhackAMoleView: View {
    private let holeCount = 9
    private let gameDuration = 30

    @State private var activeMoles: Set<Int> = []
    @State private var smashedMoles: Set<Int> = []
    @State private var score = 0
    @State private var timeLeft = 30
    @State private var isPlaying = false
    @State private var gameOver = false
    @State private var moleTimer: Timer?
    @State private var countdownTimer: Timer?

    private let columns = Array(repeating: GridItem(.flexible(), spacing: 14), count: 3)

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [Color(red: 0.15, green: 0.55, blue: 0.05),
                         Color(red: 0.35, green: 0.75, blue: 0.15)],
                startPoint: .top, endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 18) {
                Text("🔨 Whack-a-Mole")
                    .font(.system(size: 22, weight: .bold, design: .monospaced))
                    .foregroundColor(.white)

                HStack {
                    Label("\(score)", systemImage: "star.fill")
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundColor(.yellow)
                    Spacer()
                    Label("\(timeLeft)s", systemImage: "clock.fill")
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundColor(timeLeft <= 5 ? .red : .white)
                }
                .padding(.horizontal)

                LazyVGrid(columns: columns, spacing: 14) {
                    ForEach(0..<holeCount, id: \.self) { index in
                        MoleHole(
                            hasMole: activeMoles.contains(index),
                            isSmashed: smashedMoles.contains(index)
                        )
                        .onTapGesture { whack(index) }
                    }
                }
                .padding(.horizontal)

                if !isPlaying && !gameOver {
                    actionButton(label: "Start! 🔨", color: .brown) { startGame() }
                }

                if gameOver {
                    gameOverCard
                }

                Spacer()
            }
            .padding(.top)
        }
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { stopTimers() }
    }

    // MARK: – Game Over card

    private var gameOverCard: some View {
        VStack(spacing: 12) {
            Text("⏰ Time's Up!")
                .font(.system(size: 28, weight: .bold, design: .monospaced))
                .foregroundColor(.yellow)
            Text("Score: \(score) 🌟")
                .font(.system(size: 22, design: .monospaced))
                .foregroundColor(.white)
            actionButton(label: "Play Again 🔄", color: .brown) { restartGame() }
        }
        .padding(20)
        .background(Color.black.opacity(0.45))
        .cornerRadius(18)
        .padding(.horizontal)
    }

    // MARK: – Game logic

    private func startGame() {
        score = 0
        timeLeft = gameDuration
        activeMoles = []
        smashedMoles = []
        isPlaying = true
        gameOver = false

        moleTimer = Timer.scheduledTimer(withTimeInterval: 0.75, repeats: true) { _ in spawnMole() }
        countdownTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { _ in
            if timeLeft > 0 { timeLeft -= 1 } else { endGame() }
        }
    }

    private func restartGame() {
        stopTimers()
        startGame()
    }

    private func spawnMole() {
        let available = (0..<holeCount).filter { !activeMoles.contains($0) }
        guard let hole = available.randomElement() else { return }
        activeMoles.insert(hole)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.1) {
            activeMoles.remove(hole)
        }
    }

    private func whack(_ index: Int) {
        guard activeMoles.contains(index) else { return }
        activeMoles.remove(index)
        smashedMoles.insert(index)
        score += 1
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            smashedMoles.remove(index)
        }
    }

    private func endGame() {
        stopTimers()
        activeMoles = []
        isPlaying = false
        gameOver = true
    }

    private func stopTimers() {
        moleTimer?.invalidate()
        countdownTimer?.invalidate()
    }
}

// MARK: – Mole hole view

private struct MoleHole: View {
    let hasMole: Bool
    let isSmashed: Bool

    var body: some View {
        ZStack {
            Ellipse()
                .fill(Color(red: 0.3, green: 0.18, blue: 0.04))
                .frame(height: 95)

            if hasMole || isSmashed {
                Text(isSmashed ? "💫" : "🦔")
                    .font(.system(size: 54))
                    .offset(y: isSmashed ? -22 : 0)
                    .animation(.spring(response: 0.18, dampingFraction: 0.5), value: isSmashed)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .frame(height: 95)
        .animation(.spring(response: 0.25), value: hasMole)
    }
}

private func actionButton(label: String, color: Color, action: @escaping () -> Void) -> some View {
    Button(label) { action() }
        .font(.system(size: 22, weight: .bold))
        .foregroundColor(.white)
        .padding(.horizontal, 36)
        .padding(.vertical, 14)
        .background(color)
        .cornerRadius(16)
}

#Preview {
    WhackAMoleView()
}
