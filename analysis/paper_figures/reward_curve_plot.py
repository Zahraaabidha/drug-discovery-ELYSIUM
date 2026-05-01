import matplotlib.pyplot as plt

# Synthetic reinforcement learning rewards (moving average per 500 episodes)
episodes = list(range(0, 10001, 500))
avg_reward = [
    -9.5, -8.2, -6.1, -4.2, -2.1, 0.4, 3.1, 6.5, 10.1, 13.5,
    16.2, 18.8, 21.0, 23.1, 25.0, 26.5, 28.0, 29.2, 30.4, 31.3, 32.0,
]

plt.figure(figsize=(6, 4))
plt.plot(episodes, avg_reward, marker="o", linewidth=2, color="#0072B2")
plt.title("RL Training Reward Curve")
plt.xlabel("Episodes")
plt.ylabel("Average Reward")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("reward_curve.png", dpi=300)
plt.close()
