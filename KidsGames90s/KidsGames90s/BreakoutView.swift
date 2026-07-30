import SwiftUI

private struct Brick: Identifiable {
    let id: Int
    var rect: CGRect
    let color: Color
    var alive = true
}

struct BreakoutView: View {
    private let paddleW: CGFloat = 88
    private let paddleH: CGFloat = 14
    private let ballR: CGFloat = 8
    private let brickRows = 4
    private let brickCols = 7
    private let brickColors: [Color] = [.red, .orange, .yellow, .green]

    @State private var bricks: [Brick] = []
    @State private var ballPos = CGPoint.zero
    @State private var ballVel = CGPoint(x: 3, y: -5)
    @State private var paddleX: CGFloat = 0
    @State private var score = 0
    @State private var lives = 3
    @State private var isPlaying = false
    @State private var gameOver = false
    @State private var won = false
    @State private var gameTimer: Timer?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            VStack(spacing: 0) {
                headerBar

                GeometryReader { geo in
                    gameCanvas(geo: geo)
                }
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { gameTimer?.invalidate() }
    }

    // MARK: – Header

    private var headerBar: some View {
        HStack {
            Text("🧱 Breakout")
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .foregroundColor(.yellow)
            Spacer()
            Text("Score: \(score)")
                .font(.system(size: 17, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
            Text(String(repeating: "❤️", count: lives))
                .font(.system(size: 16))
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
    }

    // MARK: – Canvas

    private func gameCanvas(geo: GeometryProxy) -> some View {
        let size = geo.size
        return ZStack {
            Rectangle().fill(Color(white: 0.04))

            // Bricks
            ForEach(bricks.filter { $0.alive }) { brick in
                RoundedRectangle(cornerRadius: 5)
                    .fill(brick.color)
                    .frame(width: brick.rect.width - 4, height: brick.rect.height - 4)
                    .position(x: brick.rect.midX, y: brick.rect.midY)
            }

            // Ball
            Circle()
                .fill(Color.white)
                .frame(width: ballR * 2, height: ballR * 2)
                .position(ballPos)

            // Paddle
            RoundedRectangle(cornerRadius: 7)
                .fill(Color.cyan)
                .frame(width: paddleW, height: paddleH)
                .position(x: paddleX, y: size.height - 42)

            if !isPlaying && !gameOver && !won {
                overlayButton(label: "Tap to Play! 🧱", color: .yellow) {
                    setup(size: size)
                    startGame(size: size)
                }
            }
            if gameOver { gameOverOverlay(size: size) }
            if won      { winOverlay(size: size) }
        }
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { val in
                    paddleX = val.location.x.clamped(to: paddleW / 2 ... size.width - paddleW / 2)
                }
        )
        .onAppear { setup(size: size) }
    }

    private func gameOverOverlay(size: CGSize) -> some View {
        resultOverlay(
            title: "😵 Game Over!", titleColor: .red,
            subtitle: "Score: \(score)",
            buttonLabel: "Try Again 🔄"
        ) { setup(size: size); startGame(size: size) }
    }

    private func winOverlay(size: CGSize) -> some View {
        resultOverlay(
            title: "🎉 You Win!", titleColor: .yellow,
            subtitle: "Score: \(score)",
            buttonLabel: "Play Again 🔄"
        ) { setup(size: size); startGame(size: size) }
    }

    private func resultOverlay(
        title: String, titleColor: Color,
        subtitle: String, buttonLabel: String,
        action: @escaping () -> Void
    ) -> some View {
        VStack(spacing: 14) {
            Text(title)
                .font(.system(size: 28, weight: .bold, design: .monospaced))
                .foregroundColor(titleColor)
            Text(subtitle)
                .font(.system(size: 20, design: .monospaced))
                .foregroundColor(.white)
            overlayButton(label: buttonLabel, color: .yellow, action: action)
        }
        .padding(22)
        .background(Color.black.opacity(0.78))
        .cornerRadius(18)
    }

    private func overlayButton(label: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(label) { action() }
            .font(.system(size: 22, weight: .bold))
            .foregroundColor(.black)
            .padding(.horizontal, 30)
            .padding(.vertical, 14)
            .background(color)
            .cornerRadius(16)
    }

    // MARK: – Game logic

    private func setup(size: CGSize) {
        let bW = size.width / CGFloat(brickCols)
        let bH: CGFloat = 32
        let topPad: CGFloat = 56
        bricks = (0..<brickRows).flatMap { row in
            (0..<brickCols).map { col in
                Brick(
                    id: row * brickCols + col,
                    rect: CGRect(x: CGFloat(col) * bW, y: topPad + CGFloat(row) * bH, width: bW, height: bH),
                    color: brickColors[row % brickColors.count]
                )
            }
        }
        ballPos = CGPoint(x: size.width / 2, y: size.height / 2)
        ballVel = CGPoint(x: 3, y: -5)
        paddleX = size.width / 2
        score = 0
        lives = 3
        gameOver = false
        won = false
        isPlaying = false
    }

    private func startGame(size: CGSize) {
        isPlaying = true
        gameTimer?.invalidate()
        gameTimer = Timer.scheduledTimer(withTimeInterval: 1 / 60, repeats: true) { _ in
            updateGame(size: size)
        }
    }

    private func updateGame(size: CGSize) {
        guard isPlaying else { return }

        ballPos.x += ballVel.x
        ballPos.y += ballVel.y

        // Side walls
        if ballPos.x <= ballR || ballPos.x >= size.width - ballR {
            ballVel.x *= -1
            ballPos.x = ballPos.x.clamped(to: ballR ... size.width - ballR)
        }
        // Top wall
        if ballPos.y <= ballR {
            ballVel.y = abs(ballVel.y)
        }

        // Paddle collision (ball moving down)
        let paddleY = size.height - 42
        if ballVel.y > 0,
           ballPos.y + ballR >= paddleY - paddleH / 2,
           ballPos.y - ballR <= paddleY + paddleH / 2,
           abs(ballPos.x - paddleX) < paddleW / 2 + ballR {
            ballVel.y = -abs(ballVel.y)
            let offset = (ballPos.x - paddleX) / (paddleW / 2)
            ballVel.x = offset * 5
        }

        // Brick collisions
        for i in bricks.indices where bricks[i].alive {
            let b = bricks[i].rect
            guard ballPos.x + ballR > b.minX,
                  ballPos.x - ballR < b.maxX,
                  ballPos.y + ballR > b.minY,
                  ballPos.y - ballR < b.maxY else { continue }

            bricks[i].alive = false
            score += 10

            // Determine axis of reflection
            let overlapX = min(ballPos.x + ballR - b.minX, b.maxX - (ballPos.x - ballR))
            let overlapY = min(ballPos.y + ballR - b.minY, b.maxY - (ballPos.y - ballR))
            if overlapY < overlapX { ballVel.y *= -1 } else { ballVel.x *= -1 }
            break
        }

        // Win check
        if bricks.allSatisfy({ !$0.alive }) {
            gameTimer?.invalidate()
            won = true
            isPlaying = false
            return
        }

        // Ball falls off bottom
        if ballPos.y > size.height + ballR {
            lives -= 1
            if lives <= 0 {
                gameTimer?.invalidate()
                gameOver = true
                isPlaying = false
            } else {
                ballPos = CGPoint(x: size.width / 2, y: size.height / 2)
                ballVel = CGPoint(x: 3, y: -5)
            }
        }
    }
}

// MARK: – CGFloat clamping (shared across files via private extension in each)

private extension CGFloat {
    func clamped(to range: ClosedRange<CGFloat>) -> CGFloat {
        Swift.min(Swift.max(self, range.lowerBound), range.upperBound)
    }
}

#Preview {
    BreakoutView()
}
