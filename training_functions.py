import numpy as np
import torch
from scipy.stats import norm
from torch.autograd import Variable

from utility import gpu, cpu, MixtureModel


def unit_vector(vector):
    """Gets the unit vector version of a vector."""
    return vector.div(vector.norm() + 1e-10)


def angle_between(vector0, vector1):
    """Calculates the angle between two vectors."""
    unit_vector0 = unit_vector(vector0)
    unit_vector1 = unit_vector(vector1)
    epsilon = 1e-6
    return unit_vector0.dot(unit_vector1).clamp(-1.0 + epsilon, 1.0 - epsilon).acos()


def coefficient_estimate_loss(predicted_labels, labels, order=2):
    """Calculate the loss from the coefficient prediction."""
    return (predicted_labels[:, 0] - gpu(Variable(labels[:, 0]))).abs().pow(2).sum().pow(1/2).pow(order)


def feature_distance_loss(base_features, other_features, order=2, base_noise=0, scale=False):
    """Calculate the loss based on the distance between feature vectors."""
    base_mean_features = base_features.mean(0)
    other_mean_features = other_features.mean(0)
    if base_noise:
        base_mean_features += torch.normal(torch.zeros_like(base_mean_features), base_mean_features * base_noise)
    mean_feature_distance = (base_mean_features - other_mean_features).abs().pow(2).sum().pow(1 / 2)
    epsilon = 1e-6
    if scale:
        mean_feature_distance /= (base_mean_features.norm() + other_mean_features.norm() + epsilon)
    if order < 1:
        mean_feature_distance += epsilon
    return mean_feature_distance.pow(order)


def feature_angle_loss(base_features, other_features, target=0, summary_writer=None):
    """Calculate the loss based on the angle between feature vectors."""
    angle = angle_between(base_features.mean(0), other_features.mean(0))
    if summary_writer:
        summary_writer.add_scalar('Feature Vector/Angle', angle.data[0])
    return (angle - target).abs().pow(2)


def feature_corrcoef(x):
    """Calculate the feature vector's correlation coefficients."""
    transposed_x = x.transpose(0, 1)
    return corrcoef(transposed_x)


def corrcoef(x):
    """Calculate the correlation coefficients."""
    mean_x = x.mean(1, keepdim=True)
    xm = x.sub(mean_x)
    c = xm.mm(xm.t())
    c = c / (x.size(1) - 1)
    d = torch.diag(c)
    stddev = torch.pow(d, 0.5)
    c = c.div(stddev.expand_as(c))
    c = c.div(stddev.expand_as(c).t())
    c = torch.clamp(c, -1.0, 1.0)
    return c


def feature_covariance_loss(base_features, other_features):
    """Calculate the loss between feature vector correlation coefficient distances."""
    base_corrcoef = feature_corrcoef(base_features)
    other_corrcoef = feature_corrcoef(other_features)
    return (base_corrcoef - other_corrcoef).abs().sum()


def dnn_training_step(DNN, DNN_optimizer, dnn_summary_writer, labeled_examples, labels, settings, step):
    dnn_summary_writer.step = step
    DNN_optimizer.zero_grad()
    dnn_predicted_labels = DNN(gpu(Variable(labeled_examples)))
    dnn_loss = coefficient_estimate_loss(dnn_predicted_labels, labels) * settings.labeled_loss_multiplier
    dnn_summary_writer.add_scalar('Discriminator/Labeled Loss', dnn_loss.data[0])
    dnn_feature_layer = DNN.feature_layer
    dnn_summary_writer.add_scalar('Feature Norm/Labeled',
                                  float(cpu(dnn_feature_layer.norm(dim=1).mean()).data.numpy()))
    dnn_loss.backward()
    DNN_optimizer.step()


def gan_training_step(D, D_optimizer, G, G_optimizer, gan_summary_writer, labeled_examples, labels, settings, step,
                      unlabeled_examples):
    # Labeled.
    gan_summary_writer.step = step
    D_optimizer.zero_grad()
    predicted_labels = D(gpu(Variable(labeled_examples)))
    labeled_feature_layer = D.feature_layer
    labeled_loss = coefficient_estimate_loss(predicted_labels, labels) * settings.labeled_loss_multiplier
    gan_summary_writer.add_scalar('Discriminator/Labeled Loss', labeled_loss.data[0])
    # Unlabeled.
    gan_summary_writer.add_scalar('Feature Norm/Labeled',
                                  float(cpu(labeled_feature_layer.norm(dim=1).mean()).data.numpy()))
    _ = D(gpu(Variable(unlabeled_examples)))
    unlabeled_feature_layer = D.feature_layer
    gan_summary_writer.add_scalar('Feature Norm/Unlabeled',
                                  float(cpu(unlabeled_feature_layer.norm(dim=1).mean()).data.numpy()))
    unlabeled_loss = feature_distance_loss(unlabeled_feature_layer.detach(), labeled_feature_layer,
                                           order=settings.unlabeled_loss_order) * settings.unlabeled_loss_multiplier
    gan_summary_writer.add_scalar('Discriminator/Unlabeled Loss', unlabeled_loss.data[0])
    # Fake.
    z = torch.from_numpy(MixtureModel([norm(-settings.mean_offset, 1),
                                       norm(settings.mean_offset, 1)]
                                      ).rvs(size=[settings.batch_size, G.input_size]).astype(np.float32))
    fake_examples = G(gpu(Variable(z)), add_noise=False)
    _ = D(fake_examples.detach())
    fake_feature_layer = D.feature_layer
    fake_loss = feature_distance_loss(unlabeled_feature_layer.detach(), fake_feature_layer,
                                      order=settings.fake_loss_order).neg() * settings.fake_loss_multiplier
    gan_summary_writer.add_scalar('Discriminator/Fake Loss', fake_loss.data[0])
    # Feature norm loss.
    feature_norm_loss = (unlabeled_feature_layer.norm(dim=1).mean() - 1).pow(2) * settings.norm_loss_multiplier
    # Gradient penalty.
    alpha = gpu(Variable(torch.rand(2)))
    alpha = alpha / alpha.sum(0)
    interpolates = (alpha[0] * gpu(Variable(unlabeled_examples, requires_grad=True)) +
                    alpha[1] * gpu(Variable(fake_examples.detach().data, requires_grad=True)))
    _ = D(interpolates)
    interpolates_feature_layer = D.feature_layer
    interpolates_loss = feature_distance_loss(unlabeled_feature_layer.detach(), interpolates_feature_layer, scale=False,
                                              order=settings.fake_loss_order).neg() * settings.fake_loss_multiplier
    gradients = torch.autograd.grad(outputs=interpolates_loss, inputs=interpolates,
                                    grad_outputs=gpu(torch.ones(interpolates_loss.size())),
                                    create_graph=True, only_inputs=True)[0]
    gradient_penalty = ((gradients.norm(dim=1) - 1) ** 2).mean() * settings.gradient_penalty_multiplier
    # Discriminator update.
    loss = labeled_loss + unlabeled_loss + fake_loss + feature_norm_loss + gradient_penalty
    loss.backward()
    D_optimizer.step()
    # Generator.
    if step % settings.generator_training_step_period == 0:
        G_optimizer.zero_grad()
        _ = D(gpu(Variable(unlabeled_examples)), add_noise=False)
        unlabeled_feature_layer = D.feature_layer.detach()
        z = torch.randn(settings.batch_size, G.input_size)
        fake_examples = G(gpu(Variable(z)))
        _ = D(fake_examples)
        fake_feature_layer = D.feature_layer
        generator_loss = feature_distance_loss(unlabeled_feature_layer, fake_feature_layer,
                                               order=settings.generator_loss_order)
        gan_summary_writer.add_scalar('Generator/Loss', generator_loss.data[0])
        generator_loss.backward()
        G_optimizer.step()