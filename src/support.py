import pygame
from os import walk
from os.path import join


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


def import_subfolder_dict(path)-> dict[dict]:
    surface_dict = {
        folder: import_folder(f'{path}/{folder}') for folder in list(walk(path))[0][1]
        }
    return surface_dict

