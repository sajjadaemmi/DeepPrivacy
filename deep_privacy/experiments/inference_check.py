import torch
import numpy as np
import os
import matplotlib.pyplot as plt
from deep_privacy import torch_utils
from deep_privacy.inference import infer, deep_privacy_anonymizer
from deep_privacy.data_tools.dataloaders import load_dataset_files, cut_bounding_box
from deep_privacy.visualization import utils as vis_utils


if __name__ == "__main__":
    generator, _, _, _, _ = infer.read_args()
    imsize = generator.current_imsize
    images, bounding_boxes, landmarks = load_dataset_files("data/fdf_png", imsize,
                                                           load_fraction=True)
    batch_size = 128
    anonymizer = deep_privacy_anonymizer.DeepPrivacyAnonymizer(generator,
                                                               batch_size,
                                                               use_static_z=True)
    savedir = os.path.join(".debug", "test_examples", "inference_check")
    os.makedirs(savedir, exist_ok=True)
    num_iterations = 1
    ims_to_save = []
    percentages = [0]
    z = generator.generate_latent_variable(1, "cuda", torch.float32).zero_()
    for idx in range(-20, -1):
        orig = images[idx]
        orig = np.array(orig)
        pose = landmarks[idx:idx+1]

        assert orig.dtype == np.uint8

        to_save = orig.copy()
        to_save = vis_utils.draw_faces_with_keypoints(
            to_save, None, [infer.keypoint_to_numpy(pose*128)]
        )
        to_save = np.tile(to_save, (3, 1, 1))

        for i in range(num_iterations):
            im = orig.copy()

            bbox = bounding_boxes[idx].clone().long()
            kp = infer.keypoint_to_numpy(pose)

            kp = (kp * im.shape[1]).astype(int)
            anonymized_test = anonymizer.anonymize_images(
                [im],
                [[kp]],
                [bbox.reshape(1, -1)])[0]

            im = cut_bounding_box(im, bbox, generator.transition_value)
            orig_to_save = im.copy()
            im = torch_utils.image_to_torch(im, cuda=True, normalize_img=True)
            im = generator(im, pose, z.clone())
            im = torch_utils.image_to_numpy(im.squeeze(),
                                            to_uint8=True,
                                            denormalize=True)
            im = np.concatenate((orig_to_save.astype(np.uint8),
                                 im,
                                 anonymized_test.astype(np.uint8)),
                                axis=0)
            to_save = np.concatenate((to_save, im), axis=1)
        ims_to_save.append(to_save)
    savepath = os.path.join(savedir, f"result_image.jpg")

    ims_to_save = np.concatenate(ims_to_save, axis=0)
    plt.imsave(savepath, ims_to_save)

    print("Results saved to:", savedir)
