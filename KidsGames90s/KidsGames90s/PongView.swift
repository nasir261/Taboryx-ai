import SwiftUI

struct PongView: View {
    private let paddleW: CGFloat = 82
    private let paddleH: CGFloat = 14
    private let ballR: CGFloat = 9
    private let aiSpeedMax: CGFloat = 3.8

    @State private var ballPos = CGPoint.zero
    @State private var ballVel = CGPoint.zero
    @State private var playerX: CGFloat = 0
    @State private var aiX: CGFloat = 0
    @State private var playerScore = 0
    @State private var aiScore = 0
    @State private var isPlaying = false
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
            Text("🏓 Pong")
                .font(.system(size: 22, weight: .bold, design: .monospaced))
                .foregroundColor(.yellow)
            Spacer()
            Text("You \(playerScore)  –  \(aiScore) CPU")
                .font(.system(size: 18, weight: .bold, design: .monospaced))
                .foregroundColor(.white)
        }
        .padding(.horizontal)
        .padding(.vertical, 10)
    }

    // MARK: – Canvas

    private func gameCanvas(geo: GeometryProxy) -> some View {
        let size = geo.size
        return ZStack {
            Rectangle().fill(Color(white: 0.04))

            // Centre dashed line
            Path { p in
                p.move(to: CGPoint(x: size.width / 2, y: 0))
                p.addLine(to: CGPoint(x: size.width / 2, y: size.height))
            }
            .stroke(Color.white.opacity(0.25),
                    style: StrokeStyle(lineWidth: 2, dash: [10, 8]))

            // AI paddle (top)
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.red)
                .frame(width: paddleW, height: paddleH)
                .position(x: aiX, y: 32)

            // Player paddle (bottom)
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.cyan)
                .frame(width: paddleW, height: paddleH)
                .position(x: playerX, y: size.height - 32)

            // Ball
            Circle()
                .fill(Color.white)
                .frame(width: ballR * 2, height: ballR * 2)
                .position(ballPos)

            if !isPlaying {
                overlayStartButton(size: size)
            }
        }
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 0)
                .onChanged { val in
                    playerX = val.location.x.clamped(to: paddleW / 2 ... size.width - paddleW / 2)
                }
        )
        .onAppear { resetBall(size: size); playerX = size.width / 2; aiX = size.width / 2 }
    }

    private func overlayStartButton(size: CGSize) -> some View {
        Button("Tap to Play! 🏓") {
            resetBall(size: size)
            startGame(size: size)
        }
        .font(.system(size: 24, weight: .bold))
        .foregroundColor(.black)
        .padding(.horizontal, 30)
        .padding(.vertical, 14)
        .background(Color.yellow)
        .cornerRadius(16)
    }

    // MARK: – Game logic

    private func resetBall(size: CGSize) {
        ballPos = CGPoint(x: size.width / 2, y: size.height / 2)
        let angle = Double.random(in: -0.35...0.35)
        let speed: CGFloat = 4.5
        ballVel = CGPoint(
            x: speed * CGFloat(sin(angle)),
            y: speed * (Bool.random() ? 1 : -1)
        )
    }

    private func startGame(size: CGSize) {
        isPlaying = true
        gameTimer?.invalidate()
        gameTimer = Timer.scheduledTimer(withTimeInterval: 1 / 60, repeats: true) { _ in
            updateGame(size: size)
        }
    }

    private func updateGame(size: CGSize) {
        ballPos.x += ballVel.x
        ballPos.y += ballVel.y

        // Side walls
        if ballPos.x <= ballR || ballPos.x >= size.width - ballR {
            ballVel.x *= -1
            ballPos.x = ballPos.x.clamped(to: ballR ... size.width - ballR)
        }

        // AI tracks ball with speed cap
        let aiDiff = ballPos.x - aiX
        aiX += min(abs(aiDiff), aiSpeedMax) * (aiDiff > 0 ? 1 : -1)
        aiX = aiX.clamped(to: paddleW / 2 ... size.width - paddleW / 2)

        // Player paddle collision (ball moving down)
        let playerPaddleY = size.height - 32
        if ballVel.y > 0,
           ballPos.y + ballR >= playerPaddleY - paddleH / 2,
           ballPos.y - ballR <= playerPaddleY + paddleH / 2,
           abs(ballPos.x - playerX) < paddleW / 2 + ballR {
            ballVel.y = -abs(ballVel.y)
            ballVel.x = ((ballPos.x - playerX) / (paddleW / 2)) * 4.5
        }

        // AI paddle collision (ball moving up)
        if ballVel.y < 0,
           ballPos.y - ballR <= 32 + paddleH / 2,
           ballPos.y + ballR >= 32 - paddleH / 2,
           abs(ballPos.x - aiX) < paddleW / 2 + ballR {
            ballVel.y = abs(ballVel.y)
            ballVel.x = ((ballPos.x - aiX) / (paddleW / 2)) * 4.5
        }

        // Scoring
        if ballPos.y > size.height + ballR {
            aiScore += 1
            resetBall(size: size)
        } else if ballPos.y < -ballR {
            playerScore += 1
            resetBall(size: size)
        }
    }
}

// MARK: – CGFloat clamping helper

private extension CGFloat {
    func clamped(to range: ClosedRange<CGFloat>) -> CGFloat {
        Swift.min(Swift.max(self, range.lowerBound), range.upperBound)
    }
}

#Preview {
    PongView()
}
