import SwiftUI

private enum Direction { case up, down, left, right }

struct SnakeGameView: View {
    private let gridSize = 15
    private let cellSize: CGFloat = 22

    @State private var snake: [CGPoint] = [CGPoint(x: 10, y: 10)]
    @State private var direction: Direction = .right
    @State private var nextDirection: Direction = .right
    @State private var food: CGPoint = CGPoint(x: 15, y: 10)
    @State private var score = 0
    @State private var isGameOver = false
    @State private var isPlaying = false
    @State private var gameTimer: Timer?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()
            VStack(spacing: 14) {
                HStack {
                    Text("🐍 Snake")
                        .font(.system(size: 22, weight: .bold, design: .monospaced))
                        .foregroundColor(.yellow)
                    Spacer()
                    Text("Score: \(score)")
                        .font(.system(size: 20, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                }
                .padding(.horizontal)

                boardView

                dPad

                Spacer()
            }
            .padding(.top)
        }
        .navigationBarTitleDisplayMode(.inline)
        .onDisappear { gameTimer?.invalidate() }
    }

    // MARK: – Board

    private var boardView: some View {
        let boardSize = cellSize * CGFloat(gridSize)
        return ZStack {
            Rectangle()
                .fill(Color(red: 0.04, green: 0.12, blue: 0.04))
                .border(Color.green, width: 2)

            ForEach(0..<snake.count, id: \.self) { i in
                Rectangle()
                    .fill(i == 0 ? Color.yellow : Color.green)
                    .frame(width: cellSize - 2, height: cellSize - 2)
                    .position(
                        x: (snake[i].x + 0.5) * cellSize,
                        y: (snake[i].y + 0.5) * cellSize
                    )
            }

            Text("🍎")
                .font(.system(size: cellSize * 0.85))
                .position(x: (food.x + 0.5) * cellSize, y: (food.y + 0.5) * cellSize)

            if isGameOver {
                gameOverOverlay
            }

            if !isPlaying && !isGameOver {
                startButton(label: "Tap to Start! 🎮") { startGame() }
            }
        }
        .frame(width: boardSize, height: boardSize)
        .clipped()
    }

    private var gameOverOverlay: some View {
        VStack(spacing: 14) {
            Text("😵 Game Over!")
                .font(.system(size: 28, weight: .bold, design: .monospaced))
                .foregroundColor(.red)
            Text("Score: \(score)")
                .font(.system(size: 20, design: .monospaced))
                .foregroundColor(.white)
            Button("Play Again 🔄") { restartGame() }
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(.black)
                .padding(.horizontal, 24)
                .padding(.vertical, 10)
                .background(Color.yellow)
                .cornerRadius(12)
        }
        .padding(20)
        .background(Color.black.opacity(0.75))
        .cornerRadius(16)
    }

    // MARK: – D-Pad

    private var dPad: some View {
        VStack(spacing: 6) {
            arrowButton(.up,    icon: "arrow.up")
            HStack(spacing: 6) {
                arrowButton(.left,  icon: "arrow.left")
                Color.clear.frame(width: 68, height: 68)
                arrowButton(.right, icon: "arrow.right")
            }
            arrowButton(.down,  icon: "arrow.down")
        }
    }

    private func arrowButton(_ dir: Direction, icon: String) -> some View {
        Button { changeDirection(dir) } label: {
            Image(systemName: icon)
                .font(.system(size: 28, weight: .bold))
                .frame(width: 68, height: 68)
                .background(Color.green.opacity(0.85))
                .foregroundColor(.white)
                .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }

    // MARK: – Game Logic

    private func startGame() {
        isPlaying = true
        isGameOver = false
        gameTimer = Timer.scheduledTimer(withTimeInterval: 0.28, repeats: true) { _ in
            moveSnake()
        }
    }

    private func restartGame() {
        gameTimer?.invalidate()
        snake = [CGPoint(x: 10, y: 10)]
        direction = .right
        nextDirection = .right
        score = 0
        isGameOver = false
        spawnFood()
        startGame()
    }

    private func changeDirection(_ newDir: Direction) {
        let opposites: [Direction: Direction] = [.up: .down, .down: .up, .left: .right, .right: .left]
        if opposites[direction] != newDir {
            nextDirection = newDir
        }
    }

    private func moveSnake() {
        direction = nextDirection
        guard var head = snake.first else { return }
        switch direction {
        case .up:    head.y -= 1
        case .down:  head.y += 1
        case .left:  head.x -= 1
        case .right: head.x += 1
        }

        // Wall collision
        if head.x < 0 || head.x >= CGFloat(gridSize) || head.y < 0 || head.y >= CGFloat(gridSize) {
            triggerGameOver(); return
        }
        // Self collision
        if snake.contains(head) { triggerGameOver(); return }

        snake.insert(head, at: 0)
        if head == food {
            score += 1
            spawnFood()
        } else {
            snake.removeLast()
        }
    }

    private func spawnFood() {
        var candidate: CGPoint
        repeat {
            candidate = CGPoint(
                x: CGFloat(Int.random(in: 0..<gridSize)),
                y: CGFloat(Int.random(in: 0..<gridSize))
            )
        } while snake.contains(candidate)
        food = candidate
    }

    private func triggerGameOver() {
        gameTimer?.invalidate()
        isGameOver = true
        isPlaying = false
    }
}

// MARK: – Shared helper

private func startButton(label: String, action: @escaping () -> Void) -> some View {
    Button(label) { action() }
        .font(.system(size: 22, weight: .bold))
        .foregroundColor(.black)
        .padding(.horizontal, 28)
        .padding(.vertical, 14)
        .background(Color.green)
        .cornerRadius(16)
}

#Preview {
    SnakeGameView()
}
