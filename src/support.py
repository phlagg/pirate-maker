import pygame
from os import walk


def import_folder(path) -> list:
    surface_list = []
    for folder_name, sub_folders, img_files in walk(path):
        for image_name in img_files:
            full_path = path + "/" + image_name
            image_surf = pygame.image.load(full_path).convert_alpha()
            # add image_surf to the surface list
            surface_list.append(image_surf)
    return surface_list


def import_folder_dict(path) -> dict:
    surface_dict = {}
    for folder_name, sub_folders, img_files in walk(path):
        for image_name in img_files:
            full_path = path + "/" + image_name     
            image_surf = pygame.image.load(full_path).convert_alpha()
            # add image_surf to the surface dict
            surface_dict[image_name.split(".")[0]] = image_surf
    return surface_dict
