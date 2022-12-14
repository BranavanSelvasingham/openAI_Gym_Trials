# Landing pad is always at coordinates (0,0). Coordinates are the first
# two numbers in state vector. Reward for moving from the top of the screen
# to landing pad and zero speed is about 100..140 points. If lander moves
# away from landing pad it loses reward back. Episode finishes if the lander
# crashes or comes to rest, receiving additional -100 or +100 points.
# Each leg ground contact is +10. Firing main engine is -0.3 points each frame.
# Solved is 200 points. Landing outside landing pad is possible. Fuel is
# infinite, so an agent can learn to fly and then land on its first attempt.
# Four discrete actions available: do nothing, fire left orientation engine,
# fire main engine, fire right orientation engine.


import gym
import os
import random
import keras
import tensorflow as tf
import time
from keras import Sequential
from collections import deque
from keras.layers import Dense
from keras.optimizers import Adam
import matplotlib.pyplot as plt
from keras.activations import relu, linear
from modified_tensorboard import ModifiedTensorBoard

import numpy as np
env = gym.make('LunarLander-v2', render_mode="human")
observation = env.reset(seed=0)
np.random.seed(0)


class DQN:

    """ Implementation of deep q learning algorithm """

    def __init__(self, action_space, state_space):

        self.action_space = action_space
        self.state_space = state_space
        self.epsilon = 1.0
        self.gamma = .99
        self.batch_size = 64
        self.epsilon_min = .01
        self.lr = 0.001
        self.epsilon_decay = .996
        self.memory = deque(maxlen=1000000)

        if os.path.isfile('./latest_model/saved_model.pb'):
            print("loading existing model")
            self.model = keras.models.load_model('latest_model')
        else:
            self.model = self.build_model()
        
        print(self.model.summary())

        self.tensorboard_callback = ModifiedTensorBoard(log_dir="./logs/tensorboard_trials")


    def build_model(self):
        print("building model")

        model = Sequential()
        model.add(Dense(200, input_dim=self.state_space, activation=relu))
        model.add(Dense(150, activation=relu))
        # model.add(Dense(50, activation=relu))
        model.add(Dense(self.action_space, activation=linear))
        model.compile(loss='mse', optimizer=Adam(lr=self.lr))
        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):

        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_space)
        act_values = self.model.predict(state)
        return np.argmax(act_values[0])

    def replay(self):

        if len(self.memory) < self.batch_size:
            return

        minibatch = random.sample(self.memory, self.batch_size)
        states = np.array([i[0] for i in minibatch])
        actions = np.array([i[1] for i in minibatch])
        rewards = np.array([i[2] for i in minibatch])
        next_states = np.array([i[3] for i in minibatch])
        dones = np.array([i[4] for i in minibatch])

        states = np.squeeze(states)
        next_states = np.squeeze(next_states)

        targets = rewards + self.gamma*(np.amax(self.model.predict_on_batch(next_states), axis=1))*(1-dones)
        targets_full = self.model.predict_on_batch(states)
        ind = np.array([i for i in range(self.batch_size)])
        targets_full[[ind], [actions]] = targets

        self.model.fit(states, targets_full, epochs=1, verbose=0, callbacks=[self.tensorboard_callback])
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


def train_dqn(episode):

    loss = []
    agent = DQN(env.action_space.n, env.observation_space.shape[0])
    for e in range(episode):
        agent.tensorboard_callback.step = e
        observation, info = env.reset()
        state = np.reshape(observation, (1, 8))
        score = 0
        max_steps = 1000
        for i in range(max_steps):
            action = agent.act(state)
            env.render()
            next_state, reward, done, truncated, info = env.step(action)
            # reward -= 0.1*i
            score += reward
            next_state = np.reshape(next_state, (1, 8))
            agent.remember(state, action, reward, next_state, done)
            state = next_state
            agent.replay()
            tf.summary.scalar(name = "reward", data = reward, step = i)
            if done:
                print("episode: {}/{}, score: {}".format(e, episode, score))
                break

        loss.append(score)
        agent.tensorboard_callback.update_stats(score=score)


        # Average score of last 100 episode
        is_solved = np.mean(loss[-100:])
        if is_solved > 200:
            print('\n Task Completed! \n')
            
            break
        print("Average over last 100 episode: {0:.2f} \n".format(is_solved))
    
    agent.model.save('latest_model')
    return loss


if __name__ == '__main__':

    print(env.observation_space)
    print(env.action_space)
    episodes = 200
    loss = train_dqn(episodes)